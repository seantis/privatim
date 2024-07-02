from pyramid.httpexceptions import HTTPFound
from sqlalchemy import (
    func,
    select,
    ColumnElement,
    cast,
    literal,
    String,
)
from privatim.forms.search_form import SearchForm
from privatim.layouts import Layout
from privatim.i18n import locales, translate
from sqlalchemy import or_

from privatim.models.searchable import searchable_models
from privatim.models.comment import Comment


from typing import (TYPE_CHECKING, List, NamedTuple, Dict, Any, Optional,
                    Iterator, Sequence, )


if TYPE_CHECKING:
    from sqlalchemy.sql.selectable import Select
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session
    from sqlalchemy.dialects.postgresql.ext import websearch_to_tsquery
    from privatim.types import HasSearchableFields, RenderDataOrRedirect
    from builtins import type as type_t


class SearchResult(NamedTuple):
    id: str
    """ headlines are key value pairs of fields on various models that matched
    the search query."""
    headlines: Dict[str, str]
    type: str
    model: 'Optional[type_t[HasSearchableFields]]'  # We only load this if it
    # makes sense int he UI to display additional attributes from the model,
    #  otherwise we can save ourselves a query.


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

    def __init__(self, term: str, session: 'Session', language: str = 'de_CH'):
        self.lang: str = locales[language]
        self.session = session
        self.web_search: str = term

        self.ts_query: 'websearch_to_tsquery' = func.websearch_to_tsquery(
            self.lang, self.web_search
        )
        self.results: List[SearchResult] = []

    def do_search(self) -> None:
        for model in searchable_models():
            self.results.extend(self.search_model(model, self.ts_query))

        # Fetch Comment objects after the search
        comment_ids = [
            result.id for result in self.results if result.type == 'Comment'
        ]
        if comment_ids:
            stmt = select(Comment).filter(Comment.id.in_(comment_ids))
            comments = self.session.scalars(stmt).all()
            comment_dict: dict[str, Comment] = {
                comment.id: comment for comment in comments
            }

            # Update results with fetched Comment objects
            self.results = [
                (
                    result._replace(model=comment_dict.get(result.id))
                    if result.type == 'Comment'
                    else result
                )
                for result in self.results
            ]

    def search_model(
        self,
        model: type['HasSearchableFields'],
        ts_query: 'websearch_to_tsquery',
    ) -> List[SearchResult]:
        query = self.build_query(model, ts_query)
        raw_results = self.session.execute(query).all()
        return self.process_results(raw_results, model)

    def build_query(
        self,
        model: type['HasSearchableFields'],
        ts_query: 'websearch_to_tsquery',
    ) -> 'Select':

        headline_expression = self.generate_headlines(model, ts_query)

        select_fields: List[Any] = [
            model.id,
            *headline_expression,
            cast(literal(model.__name__), String).label('type'),  # noqa: MS001
        ]

        return select(*select_fields).filter(
            or_(*self.term_filter_text_for_model(model, self.lang))
        )

    def generate_headlines(
        self,
        model: type['HasSearchableFields'],
        ts_query: 'websearch_to_tsquery',
    ) -> List[ColumnElement[bool]]:
        """
        Generate headline expressions for all searchable fields of the model.

        Headlines in this context are snippets of text from the searchable
        fields, with the matching search terms highlighted.
        They provide context around where the search term appears in each
        field.

        Args: model (type['type[HasSearchableFields]']): The model class to
        generate headlines for. ts_query: The text search query to use for
        highlighting.

        Returns:
            List[ColumnElement]: A list of SQLAlchemy column expressions, each
            representing a headline for a searchable field. These expressions
            use the ts_headline function to generate highlighted snippets of
            text.

            See also https://www.postgresql.org/docs/current/textsearch
            -controls.html#TEXTSEARCH-HEADLINE
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
        self, model: 'type[HasSearchableFields]', language: str
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
        self, raw_results: Sequence[Any], model: 'type[HasSearchableFields]'
    ) -> List[SearchResult]:
        processed_results: List[SearchResult] = []
        for result in raw_results:
            headlines: Dict[str, str] = {
                translate(field.name.capitalize()): value
                for field in model.searchable_fields()
                if (value := getattr(result, field.name, None)) is not None
            }
            processed_results.append(
                SearchResult(
                    id=result.id,
                    headlines=headlines,
                    type=result.type,
                    model=None,
                )
            )
        return processed_results

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Iterator[SearchResult]:
        return iter(self.results)

    def __getitem__(self, index: int) -> SearchResult:
        return self.results[index]

    def __repr__(self) -> str:
        return f'<SearchResultCollection {self.results[:4]}>'


def search(request: 'IRequest') -> 'RenderDataOrRedirect':
    """
    Handle search form submission using POST/Redirect/GET pattern.

    This view processes the search form submitted via POST method, then
    redirects to avoid browser warnings on page refresh. The pattern
    prevents accidental form resubmission when users refresh the results page.


    """
    session: Session = request.dbsession
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
        result_collection: SearchCollection = SearchCollection(
            term=query, session=session
        )
        result_collection.do_search()
        return {
            'search_results': result_collection.results,
            'query': query,
            'layout': Layout(None, request),
        }

    return {
        'search_results': [],
        'query': None,
        'layout': Layout(None, request),
    }
