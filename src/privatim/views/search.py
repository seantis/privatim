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


from typing import TYPE_CHECKING, List, NamedTuple, TypeVar

if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Session, InstrumentedAttribute
    from sqlalchemy.engine.row import Row


class SearchResult(NamedTuple):
    id: int
    title: str
    headline: str
    type: str


Model = TypeVar('Model')

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
        consultation_query = self.build_query(Consultation, ts_query)
        meeting_query = self.build_query(Meeting, ts_query)
        comment_query = self.build_query(Comment, ts_query)
        union_query = union_all(
            consultation_query,
            meeting_query,
            comment_query,
        )
        raw_results = self.session.execute(union_query).all()
        self.results = self.process_results(raw_results)

    def process_results(self, raw_results) -> List[SearchResult]:
        processed_results = []
        for result in raw_results:
            try:
                processed_results.append(
                    SearchResult(
                        id=result.id,
                        title=result.title,
                        headline=result.headline,
                        type=result.type,
                    )
                )
            except AttributeError as e:
                print(f"Error processing result: {e}")
        return processed_results

    def build_query(self, model: Model, ts_query):
        search_fields: List[InstrumentedAttribute] = list(
            model.searchable_fields()
        )
        headline_expr = self.generate_headline(model, ts_query)

        return select(
            model.id,
            search_fields[0].label(
                'title'
            ),  # Using the first searchable field for the title
            headline_expr,
            cast(literal(model.__name__), String).label('type'),
        ).filter(or_(*self.term_filter_text_for_model(model, self.lang)))

    def generate_headline(self, model: Model, ts_query):
        """The generate_headline method concatenates all searchable
        fields into a single string, separated by ' | '. This ensures that all
        searchable fields are included in the headline."""

        search_fields = model.searchable_fields()
        headline_fields = [func.coalesce(field, '') for field in search_fields]
        concatenated_fields = func.concat_ws(' | ', *headline_fields)

        # https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-HEADLINE
        return func.ts_headline(
            self.lang,
            concatenated_fields,
            ts_query,
            'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, '
            'ShortWord=3, HighlightAll=TRUE, MaxFragments=3, '
            'FragmentDelimiter=" ... "',
        ).label('headline')

    def term_filter_text_for_model(
        self, model: Model, lang: str
    ) -> List[ColumnElement[bool]]:
        def match(
            column: ColumnElement[str], language: str
        ) -> ColumnElement[bool]:
            return column.op('@@')(
                func.websearch_to_tsquery(language, self.web_search)
            )

        def match_convert(
            column: ColumnElement[str], language: str
        ) -> ColumnElement[bool]:
            return match(func.to_tsvector(language, column), language)

        return [
            match_convert(field, lang) for field in model.searchable_fields()
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
