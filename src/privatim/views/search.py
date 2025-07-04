from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import (func, select, literal, Select, Function,
                        BinaryExpression, type_coerce, or_)

from privatim.forms.search_form import SearchForm
from privatim.layouts import Layout
from privatim.i18n import locales
from privatim.models import AgendaItem
from privatim.models.file import SearchableFile
from privatim.models.searchable import searchable_models
from privatim.models.searchable import SearchableMixin
from privatim.models.markup_text_type import MarkupText


from typing import TYPE_CHECKING, NamedTuple, TypedDict, Any, TypeVar, Union
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from privatim.types import RenderDataOrRedirect

T = TypeVar('T', bound=Union[BinaryExpression[Any], Function[Any]])


class SearchResult(NamedTuple):
    """ The id (UUIDStrPK) of the instance """
    id: str

    """ headlines are key value pairs of fields on various models that matched
    the search query."""
    headlines: dict[str, str]

    """ The literal model.__name__ for distinction in search_results.pt. """
    type: str

    """ The specific model instance where the search was found.
    Nullable, because should not be fetched by default.
    We only load this if it makes sense in he UI to display additional
    attributes (as part of a search result element) otherwise we
    can save ourselves a query. """
    model_instance: SearchableMixin | SearchableFile | None = None


class SearchResultType(TypedDict):
    id: str
    headlines: dict[str, str]
    type: str


class FileSearchResultType(TypedDict):
    id: str
    headlines: dict[str, str]
    type: str
    model: SearchableFile


class SearchCollection:

    """
     Integrates PostgreSQL full-text search. Models can derive from
    `SearchableMixin` and implement `searchable_fields` for column searches.


    Key features:
    - Supports searching in both model attributes and associated files
    - Generates highlighted snippets (headlines) of matching text
    - We use websearch_to_tsquery, which automatically converts the search term
    into a tsquery.

    | term | tsquery |
    |------|---------|
    | the donkey | 'donkey' |
    | "blue donkey" | 'blue' & 'donkey' |

    This supports common, well-known search syntax used by many popular
    search engines. For instance, you can use double quotes to search for an
    exact phrase. Or negate a term with a minus sign.

    See also this blog:
    https://adamj.eu/tech/2024/01/03/postgresql-full-text-search-websearch/

    """

    def __init__(self, term: str, session: 'Session', language: str = 'de_CH'):
        self.lang: str = locales[language]
        self.session = session
        self.web_search = term
        self.ts_query = func.websearch_to_tsquery(self.lang, self.web_search)
        self.results: list[SearchResult] = []

    def do_search(self) -> None:
        for model in searchable_models():
            self.results.extend(self.search_model(model))

        self._add_agenda_items_to_results()

    def search_model(
        self, model: type[SearchableMixin | SearchableFile]
    ) -> list[SearchResult]:
        attribute_results = []
        if issubclass(model, SearchableMixin):
            attribute_results = self.search_in_columns(model)

        if issubclass(model, SearchableFile):
            file_results = self.search_in_model_files(model)
            return attribute_results + file_results

        return attribute_results

    def search_in_columns(
        self, model: type[SearchableMixin]
    ) -> list[SearchResult]:
        query = self.build_attribute_query(model)

        raw_results = self.session.execute(query)
        return [
            SearchResult(
                id=result.id,
                headlines={
                    field.name.capitalize(): getattr(result, field.name)
                    for field in model.searchable_fields()
                    if getattr(result, field.name) is not None
                },
                type=result.type,
                model_instance=None,
            )
            for result in raw_results
        ]

    def search_in_model_files(
        self, model: type[SearchableFile]
    ) -> list[SearchResult]:
        query = self.build_file_query(model)
        results_list = []
        for result in self.session.execute(query):
            search_result = SearchResult(
                id=result.id,
                headlines={
                    'file_content_headline': Markup(
                        result.file_content_headline
                    )},
                type='SearchableFile',
                model_instance=result.SearchableFile
            )

            results_list.append(search_result)
        return results_list

    def build_file_query(
            self, model: type[SearchableFile]
    ) -> 'Select[tuple[FileSearchResultType, ...]]':
        """ Search in the files.

        Two distinct things are happening here:

         1. Generate headline expressions for all searchable fields of the
        model. Headlines in this context are snippets of text from the
        file, with the matching search terms highlighted. They
        provide context around where the search term appears in each field.
        Note: ts_headlines requires the original document text, not tsvector.


        2. The actual search happens in the tsvector type searchable_text_{
        locale}, which as been indexed beforehand.
        """

        return (
            select(
                model.id,
                func.ts_headline(
                    self.lang,
                    SearchableFile.extract,
                    self.ts_query,
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=25, '
                    'MinWords=15, ShortWord=3, HighlightAll=FALSE, '
                    'MaxFragments=3, FragmentDelimiter=" ... "',
                ).label('file_content_headline'),
                SearchableFile,
                literal('SearchableFile').label('type')
            )
            .select_from(model)
            .filter(model.searchable_text_de_CH.op('@@')(self.ts_query))
        )

    def build_attribute_query(
        self, model: type[SearchableMixin]
    ) -> 'Select[tuple[SearchResultType, ...]]':

        headline_expressions = (
            type_coerce(func.ts_headline(
                self.lang,
                field,
                self.ts_query,
                'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, '
                'ShortWord=3, HighlightAll=FALSE, MaxFragments=3, '
                'FragmentDelimiter=" ... "',
            ), MarkupText).label(field.key)
            for field in model.searchable_fields()
        )

        select_fields = [
            model.id,
            *headline_expressions,
            literal(model.__name__).label('type'),
        ]

        return select(*select_fields).filter(
            or_(
                *[
                    func.to_tsvector(self.lang, field).op('@@')(self.ts_query)
                    for field in model.searchable_fields()
                ]
            )
        )

    def _add_agenda_items_to_results(self) -> None:
        """Extends self.results with the complete model for AgendaItem.

        Our initial search query intentionally avoided loading complete model
        instances for each result - a performance optimization. By querying
        only `id`, we enable selective full-model retrieval after the primary
        search completes, preventing unnecessary data overhead.

        Currently, AgendaItems are the only SearchResult type requiring full
        model retrieval to support additional functionality.
        """

        agenda_item_ids = [
            result.id
            for result in self.results
            if result.type.lower() == 'agendaitem'
        ]
        if agenda_item_ids:
            stmt = select(AgendaItem).filter(
                AgendaItem.id.in_(agenda_item_ids)
            )
            agenda_item_dict: dict[str, AgendaItem] = {
                agenda_item.id: agenda_item
                for agenda_item in self.session.scalars(stmt).all()
            }
            self.results = [
                (
                    result._replace(
                        model_instance=agenda_item_dict.get(result.id)
                    )
                    if result.type.lower() == 'agendaitem'
                    else result
                )
                for result in self.results
            ]

    def __repr__(self) -> str:
        output = ''
        for res in self.results:
            output += f'type: {res.type}\n'
            output += f'id: {res.id}\n'
        return output


def search(request: 'IRequest') -> 'RenderDataOrRedirect':
    """
    Handle search form submission using POST/Redirect/GET design pattern.

    This view processes the search form submitted via POST method, then
    redirects to avoid browser warnings on page refresh. This prevents
    accidental form resubmission if users refresh the results page.

    """
    session = request.dbsession
    form: SearchForm = SearchForm(request)
    if request.method == 'POST' and form.validate():
        assert form.term.data is not None
        return HTTPFound(
            location=request.route_url(
                'search',
                _query={'q': form.term.data},
            )
        )

    query = request.GET.get('q')
    if query:
        collection: SearchCollection = SearchCollection(
            term=query, session=session
        )
        collection.do_search()
        search_results = []
        for result in collection.results:
            result_dict = result._asdict()  # Convert NamedTuple to dict

            if result.type == 'SearchableFile':
                file = result.model_instance
                assert isinstance(file, SearchableFile)
                result_dict['file_name'] = file.filename
                result_dict['file_link'] = request.route_url(
                    'download_file', id=file.id
                )
                # Determine the icon based on content type
                if (
                    file.content_type == 'application/vnd.openxmlformats-'
                                         'officedocument.wordprocessingml.'
                                         'document'
                ):
                    result_dict['icon_url'] = request.static_url(
                        'privatim:static/docx.svg'
                    )
                    result_dict['icon_alt'] = 'DOCX File Icon'
                elif file.content_type == 'application/pdf':
                    result_dict['icon_url'] = request.static_url(
                        'privatim:static/PDF_file_icon_with_primary_color.svg'
                    )
                    result_dict['icon_alt'] = 'PDF File Icon'
                else:
                    result_dict['icon_url'] = request.static_url(
                        'privatim:static/generic_file_icon.svg'
                    )
                    result_dict['icon_alt'] = 'Generic File Icon'

            if result.type in ['AgendaItem', 'Consultation', 'Meeting']:
                first_item = next(iter(result_dict['headlines'].items()))
                result_dict['headlines']['title'] = first_item[1]

            search_results.append(result_dict)
        return {
            'search_results': search_results,
            'query': query,
            'layout': Layout(None, request),
        }

    return {
        'search_results': [],
        'query': None,
        'layout': Layout(None, request),
    }

