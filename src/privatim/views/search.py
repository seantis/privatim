from sqlalchemy import func, select, ColumnElement, union_all, text, cast, \
    literal, String
from privatim.forms.search_form import SearchForm
from privatim.models import Consultation, Meeting
from privatim.i18n import locales
from sqlalchemy import or_

from privatim.models.comment import Comment
from privatim.models.searchable import searchable_models


from typing import TYPE_CHECKING, List, NamedTuple, Protocol
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from sqlalchemy.orm import Query, Session


class SearchResultCollection:
    web_search: str
    results: list

    def __init__(self, term: str, session: 'Session', language='de_CH'):
        self.lang = locales[language]
        self.session = session
        self.web_search = term
        self.results = []

    def do_search(self) -> None:
        """ Main interface for getting the search results from templates"""
        ts_query = func.websearch_to_tsquery(self.lang, self.web_search)

        consultation_query = select(
            Consultation.id,
            Consultation.title.label('title'),
            Consultation.description.label('description'),
            func.ts_headline(self.lang, Consultation.description, ts_query).label('headline'),
            func.ts_rank_cd(func.to_tsvector(self.lang, Consultation.title + ' ' + Consultation.description), ts_query).label('rank'),
            cast(literal("'consultation'"), String).label('type')
        ).filter(or_(*self.term_filter_text_for_model(Consultation, self.lang)))

        meeting_query = select(
            Meeting.id,
            Meeting.name.label('title'),
            Meeting.decisions.label('description'),
            func.ts_headline(self.lang, Meeting.decisions, ts_query).label('headline'),
            func.ts_rank_cd(func.to_tsvector(self.lang, Meeting.name + ' ' + Meeting.decisions), ts_query).label('rank'),
            cast(literal("'meeting'"), String).label('type')
        ).filter(or_(*self.term_filter_text_for_model(Meeting, self.lang)))

        # comment_query = select(
        #     Comment.id,
        #     Comment.content.label('title'),
        #     Comment.content.label('description'),
        #     func.ts_headline(self.lang, Comment.content, ts_query).label('headline'),
        #     func.ts_rank_cd(func.to_tsvector(self.lang, Comment.content), ts_query).label('rank'),
        #     func.literal('Comment').label('type')
        # ).filter(or_(*self.term_filter_text_for_model(Comment, self.lang)))

        union_query = union_all(consultation_query, meeting_query).order_by(
            text('rank DESC')
        )
        self.results = list(self.session.execute(union_query).all())

    def term_filter_text_for_model(self, model, language: str) -> list['ColumnElement[bool]']:
        """ Returns a list of SqlAlchemy filter statements matching possible
        fulltext attributes based on the term for a given model."""
        def match(
                column: 'ColumnElement[str] | ColumnElement[str | None]',
                language: str
        ) -> 'ColumnElement[bool]':
            return column.op('@@')(func.websearch_to_tsquery(language, self.web_search))

        def match_convert(
                column: 'ColumnElement[str] | ColumnElement[str | None]',
                language: str
        ) -> 'ColumnElement[bool]':
            return match(func.to_tsvector(language, column), language)

        if model == Consultation:
            return [
                match_convert(Consultation.title, language),
                match_convert(Consultation.description, language),
            ]
        elif model == Meeting:
            return [
                match_convert(Meeting.name, language),
                match_convert(Meeting.decisions, language),
            ]
        elif model == Comment:
            return [
                match_convert(Comment.content, language),
            ]
        else:
            return []
    
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

        result_collection = SearchResultCollection(term=query, session=session)
        result_collection.do_search()
        breakpoint()

        return {'search_results': result_collection}
