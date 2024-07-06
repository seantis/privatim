from markupsafe import Markup
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import (func, select, literal, Select)
from privatim.forms.search_form import SearchForm
from privatim.layouts import Layout
from privatim.i18n import locales

from privatim.models import SearchableAssociatedFiles
from privatim.models.file import SearchableFile
from privatim.models.searchable import searchable_models
from privatim.models.comment import Comment


from typing import (TYPE_CHECKING, NamedTuple, Optional,
                    TypedDict)
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from privatim.types import HasSearchableFields, RenderDataOrRedirect


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
    model_instance: 'Optional[HasSearchableFields | SearchableFile]' = None


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

    """ Provides PostgreSQL full text search ingegration.

    We use websearch_to_tsquery, which automatically converts the search term
    into a tsquery.

    | term | tsquery |
    |------|---------|
    | the donkey | 'donkey' |
    | "blue donkey" | 'blue' & 'donkey' |

    See also:
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

        self._add_comments_to_results()

    def search_model(
        self, model: type['HasSearchableFields']
    ) -> list[SearchResult]:
        attribute_results = self.search_in_columns(model)

        if issubclass(model, SearchableAssociatedFiles):
            file_results = self.search_in_model_files(model)
            return attribute_results + file_results

        return attribute_results

    def search_in_columns(
        self, model: type['HasSearchableFields']
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
        self, model: SearchableAssociatedFiles
    ) -> list[SearchResult]:
        query = self.build_file_query(model)
        results_list = []
        for result in self.session.execute(query):
            search_result = SearchResult(
                id=result.id,
                headlines={
                    'file_content_headline': Markup(   # noqa: MS001
                        result.file_content_headline
                    )},
                type='SearchableFile',
                model_instance=result.SearchableFile
            )

            results_list.append(search_result)
        return results_list

    def build_file_query(
            self, model: type[SearchableAssociatedFiles]
    ) -> 'Select[FileSearchResultType]':
        """ Search in the files.

        Two distinct things are happening here:

         1. Generate headline expressions for all searchable fields of the
        model. Headlines in this context are snippets of text from the
        fiel, with the matching search terms highlighted. They
        provide context around where the search term appears in each field.
        ts_headlines requires the original document text, not tsvector.


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
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, '
                    'MinWords=15, ShortWord=3, HighlightAll=FALSE, '
                    'MaxFragments=3, FragmentDelimiter=" ... "',
                ).label('file_content_headline'),
                SearchableFile,
                literal('SearchableFile').label('type')
            )
            .select_from(model)
            .join(SearchableFile, model.files)
            .filter(model.searchable_text_de_CH.op('@@')(self.ts_query))
        )

    def build_attribute_query(
            self, model: type['HasSearchableFields']
    ) -> 'Select[SearchResultType]':

        headline_expressions = [
            func.ts_headline(
                self.lang,
                field,
                self.ts_query,
                'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, '
                'ShortWord=3, HighlightAll=FALSE, MaxFragments=3, '
                'FragmentDelimiter=" ... "',
            ).label(field.key)
            for field in model.searchable_fields()
        ]

        combined_vector = self._create_rank_expression(model)
        rank_expression = func.ts_rank(combined_vector, self.ts_query)
        select_fields = [
            model.id,
            *headline_expressions,
            literal(model.__name__).label('type'),  # noqa: MS001
            rank_expression.label('rank')
        ]

        return (
            select(*select_fields)
            .filter(combined_vector.op('@@')(self.ts_query))
            .order_by(rank_expression.desc())
        )

    def _create_rank_expression(self, model):
        """ Weight the search results based on the importance of the field.

        - 1.0 for primary fields (A)
        - 0.4 for high importance fields (B)
        - 0.2 for medium importance fields (C)
        - 0.1 for low importance fields (D)

        See also:
        https://www.postgresql.org/docs/current/textsearch-controls.html
        #TEXTSEARCH-RANKING

        Not all search matches hold equal importance. I assume matches in
        model.title should rank higher in the search results. To achieve
        this, we'll mark columns decorated with @prioritize_search_field as
        'A', and all other columns as 'B'. (And we use this decorator approach
        because the field name is not always literally 'title'.)

        """

        weights = {'primary': 'A', 'high': 'B', 'medium': 'C', 'low': 'D'}
        # Create weighted vectors using list comprehension
        weighted_vectors = [
            func.setweight(
                func.to_tsvector(self.lang, field),
                (
                    weights['primary']
                    if getattr(field, 'is_primary_search_field', False)
                    else weights['high']
                ),
            )
            for field in model.searchable_fields()
        ]
        # Combine all weighted vectors
        if weighted_vectors:
            combined_vector = weighted_vectors[0]
            for vector in weighted_vectors[1:]:
                combined_vector = combined_vector.op('||')(vector)
        else:
            combined_vector = func.to_tsvector('')
        return combined_vector,

    def _add_comments_to_results(self) -> None:
        """Extends self.results with the complete query for Comment.

        This is for displaying more information in the search results.
        """
        comment_ids = [
            result.id for result in self.results if result.type == 'Comment'
        ]
        if comment_ids:
            stmt = select(Comment).filter(Comment.id.in_(comment_ids))
            comments = self.session.scalars(stmt).all()
            comment_dict: dict[str, Comment] = {
                comment.id: comment for comment in comments
            }
            self.results = [
                (
                    result._replace(model_instance=comment_dict.get(result.id))
                    if result.type == 'Comment'
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
            if result.type == 'Comment':
                result.headlines['Content'] = Markup(  # noqa: MS001
                    result.headlines['Content']
                )

            if result.type in ['AgendaItem', 'Consultation', 'Meeting']:
                first_item = next(iter(result.headlines.items()))
                result.headlines['title'] = first_item[1]

            search_results.append(result)

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
