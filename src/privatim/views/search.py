from sqlalchemy import func, select, ColumnElement
from privatim.forms.search_form import SearchForm
from privatim.models import Consultation
from privatim.i18n import locales
from sqlalchemy import or_

from privatim.models.searchable import searchable_models


from typing import TYPE_CHECKING, List, NamedTuple, Protocol
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Query


class SearchResult(NamedTuple):
    id: int
    title: str
    model_type: str
    description: str
    rank: float
    url: str


class SortingStrategy(Protocol):
    def sort(self, results: List[SearchResult]) -> List[SearchResult]: ...


class RankSortStrategy:
    def sort(self, results: List[SearchResult]) -> List[SearchResult]:
        return sorted(results, key=lambda x: x.rank, reverse=True)


class AlphabeticalSortStrategy:
    def sort(self, results: List[SearchResult]) -> List[SearchResult]:
        return sorted(results, key=lambda x: x.title.lower())


class ModelTypeSortStrategy:
    def sort(self, results: List[SearchResult]) -> List[SearchResult]:
        return sorted(results, key=lambda x: (x.model_type, -x.rank))


class SearchResultCollection:
    term: str
    results: List[SearchResult]
    sorting_strategy: SortingStrategy = AlphabeticalSortStrategy()

    def __init__(self, term: str, session: 'Session', language='de_CH'):
        lang = locales[language]
        self.session = session
        self.term = func.websearch_to_tsquery(lang, term)
        self.results = []
        self.sorting_strategy = AlphabeticalSortStrategy()

    def query(self) -> 'Query[SwissVote]':

        query = self.session.query(Consultation)
        query = query.filter(or_(*self.term_filter))
        return query

    @property
    def term_filter(self) -> list['ColumnElement[bool]']:
        """ Returns a list of SqlAlchemy filter statements based on the search
        term.

        """

        return self.term_filter_text

    def __post_init__(self):
        query = self.query()
        # create : List[SearchResult] from the qeury
        

        self.results = self.perform_()

    def sort_results(self):
        self.results = self.sorting_strategy.sort(self.results)

    def set_sorting_strategy(self, strategy: SortingStrategy):
        self.sorting_strategy = strategy

    @property
    def term_filter_text(self) -> list['ColumnElement[bool]']:
        """ Returns a list of SqlAlchemy filter statements matching possible
        fulltext attributes based on the term.

        """

        if not self.term:
            return []

        def match(
                column: 'ColumnElement[str] | ColumnElement[str | None]',
                language: str
        ) -> 'ColumnElement[bool]':
            return column.op('@@')(func.to_tsquery(language, self.term))

        def match_convert(
                column: 'ColumnElement[str] | ColumnElement[str | None]',
                language: str
        ) -> 'ColumnElement[bool]':
            return match(func.to_tsvector(language, column), language)

        return [
            match(Consultation.searchable_text_de_CH, 'german'),
        ]

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, index):
        return self.results[index]


def search(request: 'IRequest'):
    session = request.dbsession
    form = SearchForm(request)
    if request.method == 'POST' and form.validate():
        query = request.POST['search']

        # todo:remove later
        stmt = select(Consultation.searchable_text_de_CH)
        assert None not in session.execute(stmt).scalars().all()

        result_collection = SearchResultCollection(query, session)

        return {'search_results': result_collection}
