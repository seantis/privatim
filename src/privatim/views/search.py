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
from privatim.i18n import locales
from sqlalchemy import or_

from privatim.models.comment import Comment


from typing import TYPE_CHECKING, List, NamedTuple

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session, InstrumentedAttribute
    from sqlalchemy.engine.row import Row


class SearchResult(NamedTuple):
    id: int
    title: str
    headline: str
    type: str


class SearchCollection:
    """ A class for searching the database for a given term.

    We use websearch_to_tsquery, which automatically converts the search term
    into a tsquery.

    | term | tsquery |
    |------|---------|
    | the donkey |	|'donkey' |
    | "blue donkey" | 'blue' & 'donkey' |

    See also:
    https://adamj.eu/tech/2024/01/03/postgresql-full-text-search-websearch/

    """
    web_search: str
    results: list

    def __init__(self, term: str, session: 'Session', language='de_CH'):
        self.lang = locales[language]
        self.session = session
        self.web_search = term
        self.results = []

    def do_search(self) -> None:
        """Main interface for getting the search results."""
        ts_query = func.websearch_to_tsquery(self.lang, self.web_search)

        consultation_query = self.build_query(
            Consultation, ts_query, 'Consultation'
        )
        meeting_query = self.build_query(Meeting, ts_query, 'Meeting')
        comment_query = self.build_query(Comment, ts_query, 'Comment')

        union_query = union_all(
            consultation_query, meeting_query, comment_query
        )

        results = self.session.execute(union_query).all()
        self.results = [SearchResult(*result) for result in results]
        breakpoint()

    def build_query(self, model, ts_query, model_name: str):
        search_fields: list[InstrumentedAttribute] = list(
            model.searchable_fields()
        )

        headline_expr = func.ts_headline(
            self.lang,
            search_fields[0],  # using the first searchable field as the
            # headline
            ts_query,
            'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, ShortWord=3, HighlightAll=FALSE, MaxFragments=3, FragmentDelimiter=" ... "',
        ).label('headline')

        return select(
            model.id,  # include the model itself in the search results
            search_fields[0].label('title'),  # Using the first searchable
            # field for the title
            headline_expr,
            cast(literal(model_name), String).label('type'),
        ).filter(or_(*self.term_filter_text_for_model(model, self.lang)))

    def term_filter_text_for_model(
        self, model, language: str
    ) -> list['ColumnElement[bool]']:
        """Returns a list of SqlAlchemy filter statements matching possible
        fulltext attributes based on the term for a given model."""

        def match(
            column: 'ColumnElement[str] | ColumnElement[str | None]',
            language: str,
        ) -> 'ColumnElement[bool]':
            return column.op('@@')(
                func.websearch_to_tsquery(language, self.web_search)
            )

        def match_convert(
            column: 'ColumnElement[str] | ColumnElement[str | None]',
            language: str,
        ) -> 'ColumnElement[bool]':
            return match(func.to_tsvector(language, column), language)

        return [
            match_convert(field, language)
            for field in model.searchable_fields()
        ]

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, index):
        return self.results[index]

    def __repr__(self) -> str:
        # diplay the self.results, the first 4
        return f'<SearchResultCollection {self.results[:4]}>'


def search(request: 'IRequest'):
    session = request.dbsession
    form = SearchForm(request)
    if request.method == 'POST' and form.validate():
        query = request.POST['search']

        # todo:remove later
        stmt = select(Consultation.searchable_text_de_CH)
        assert None not in session.execute(stmt).scalars().all()

        result_collection = SearchCollection(term=query, session=session)
        result_collection.do_search()

        activities = result_collection.results
        return {'activities': activities}
