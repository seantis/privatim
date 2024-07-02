from pyramid.httpexceptions import HTTPFound
from sqlalchemy import (
    func,
    select,
    ColumnElement,
    union_all,
    cast,
    literal,
    String,
)
from privatim.forms.search_form import SearchForm
from privatim.models import Consultation, Meeting
from privatim.i18n import locales, translate
from privatim.i18n import _
from sqlalchemy import or_

from privatim.models.comment import Comment


from typing import TYPE_CHECKING, List, NamedTuple, TypeVar

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session, InstrumentedAttribute


class SearchResult(NamedTuple):
    id: int
    """ headlines are key value pairs of fields on various models that matched
    the search query."""
    headlines: dict[str, str]
    type: str


Model = TypeVar('Model')


class SearchCollection:
    """A class for searching the database for a given term.

    We use websearch_to_tsquery, which automatically converts the search term
    into a tsquery.

    | term | tsquery |
    |------|---------|
    | the donkey |	|'donkey' |
    | "blue donkey" | 'blue' & 'donkey' |

    See also:
    https://adamj.eu/tech/2024/01/03/postgresql-full-text-search-websearch/

    """

    def __init__(self, term: str, session: 'Session', language='de_CH'):
        self.lang = locales[language]
        self.session = session
        self.web_search = term
        self.ts_query = func.websearch_to_tsquery(self.lang, self.web_search)
        self.results: List[SearchResult] = []
        self.models = [Consultation, Meeting, Comment]

    def do_search(self) -> None:
        for model in self.models:
            self.results.extend(self.search_model(model, self.ts_query))

    def search_model(self, model: type[Model], ts_query) -> List[SearchResult]:
        query = self.build_query(model, ts_query)
        raw_results = self.session.execute(query).all()
        return self.process_results(raw_results, model)

    def build_query(self, model: type[Model], ts_query):

        headline_exprs = self.generate_headlines(model, ts_query)

        select_fields = [
            model.id,
            *headline_exprs,
            cast(literal(model.__name__), String).label('type'),
        ]

        return select(*select_fields).filter(
            or_(*self.term_filter_text_for_model(model, self.lang))
        )

    def generate_headlines(self, model: type[Model], ts_query):
        """
        Generate headline expressions for all searchable fields of the model.

        Headlines in this context are snippets of text from the searchable
        fields, with the matching search terms highlighted.
        They provide context around where the search term appears in each field.

        Args:
            model (type[Model]): The model class to generate headlines for.
            ts_query: The text search query to use for highlighting.

        Returns:
            List[ColumnElement]: A list of SQLAlchemy column expressions, each
            representing a headline for a searchable field. These expressions
            use the ts_headline function to generate highlighted snippets of
            text.
        """
        return [
            func.ts_headline(
                self.lang,
                field,
                ts_query,
                'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, '
                'ShortWord=3, HighlightAll=FALSE, MaxFragments=3, '
                'FragmentDelimiter=" ... "',
            ).label(field.name)
            for field in model.searchable_fields()
        ]

    def term_filter_text_for_model(
            self, model: type[Model], language: str
    ) -> List[ColumnElement[bool]]:
        def match(
                column: ColumnElement[str],
        ) -> ColumnElement[bool]:
            return column.op('@@')(self.ts_query)

        def match_convert(
                column: ColumnElement[str], language: str
        ) -> ColumnElement[bool]:
            return match(func.to_tsvector(language, column))

        return [
            match_convert(field, language)
            for field in model.searchable_fields()
        ]

    def process_results(
            self, raw_results, model: type[Model]
    ) -> List[SearchResult]:
        searchable = list(model.searchable_fields())
        processed_results = []
        for result in raw_results:
            headlines = {
                field.name: value
                for field in searchable
                if (value := getattr(result, field.name, None)) is not None
            }
            processed_results.append(
                SearchResult(
                    id=result.id,
                    headlines=headlines,
                    type=result.type,
                )
            )
        return processed_results

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, index):
        return self.results[index]

    def __repr__(self) -> str:
        return f'<SearchResultCollection {self.results[:4]}>'


def search(request: 'IRequest'):
    """
    Handle search form submission using POST/Redirect/GET pattern.

    This view processes the search form submitted via POST method, then
    redirects to avoid browser warnings on page refresh. The pattern
    prevents accidental form resubmission when users refresh the results page.


    """
    session = request.dbsession
    form = SearchForm(request)

    if request.method == 'POST' and form.validate():
        query = form.term.data
        return HTTPFound(location=request.route_url('search', _query={'q': query}))

    query = request.GET.get('q')
    if query:
        result_collection = SearchCollection(term=query, session=session)
        result_collection.do_search()

        translated_results = []
        for result in result_collection.results:
            headlines_with_translated_keys = {
                translate(key.capitalize()): value
                for key, value in result.headlines.items()
            }
            translated_results.append(SearchResult(
                id=result.id,
                headlines=headlines_with_translated_keys,
                type=result.type
            ))

        return {'search_results': translated_results, 'query': query}

    return {'search_results': [], 'query': None}
