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


class SearchResult(NamedTuple):
    id: int
    title: str
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
        self.results: List[SearchResult] = []
        self.models = [Consultation, Meeting, Comment]

    def do_search(self) -> None:
        ts_query = func.websearch_to_tsquery(self.lang, self.web_search)
        for model in self.models:
            self.results.extend(self.search_model(model, ts_query))

    def search_model(self, model: type[Model], ts_query) -> List[SearchResult]:
        query = self.build_query(model, ts_query)
        raw_results = self.session.execute(query).all()
        return self.process_results(raw_results, model)

    def build_query(self, model: type[Model], ts_query):
        search_fields: List[InstrumentedAttribute] = list(
            model.searchable_fields()
        )
        headline_exprs = self.generate_headlines(model, ts_query)

        select_fields = [
            model.id,
            search_fields[0].label('title'),
            *headline_exprs,
            cast(literal(model.__name__), String).label('type'),
        ]

        return select(*select_fields).filter(
            or_(*self.term_filter_text_for_model(model, self.lang))
        )

    def generate_headlines(self, model: type[Model], ts_query):
        search_fields = list(model.searchable_fields())
        return [
            func.ts_headline(
                self.lang,
                field,
                ts_query,
                'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, ShortWord=3, HighlightAll=FALSE, MaxFragments=3, FragmentDelimiter=" ... "',
            ).label(field.name)
            for field in search_fields[
                1:
            ]  # Skip the first field as it's used for the title
        ]

    def term_filter_text_for_model(
        self, model: type[Model], language: str
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
            match_convert(field, language)
            for field in model.searchable_fields()
        ]

    def process_results(
        self, raw_results, model: type[Model]
    ) -> List[SearchResult]:
        searchable = list(model.searchable_fields())
        processed_results = []
        field_names = [field.name for field in searchable[1:]]
        for result in raw_results:
            headlines = {
                field_name: getattr(result, field_name)
                for field_name in field_names
                if getattr(result, field_name)
            }
            processed_results.append(
                SearchResult(
                    id=result.id,
                    title=result.title,
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
    session = request.dbsession
    form = SearchForm(request)
    if request.method == 'POST' and form.validate():
        query = request.POST['search']

        result_collection = SearchCollection(term=query, session=session)
        result_collection.do_search()

        activities = result_collection.results
        return {'activities': activities}
