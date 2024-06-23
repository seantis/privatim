from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import AgendaItem, GeneralFile
from privatim.models.commentable import Comment
from privatim.models import WorkingGroup, Consultation, User, Meeting

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.models.root import Root


_working_group_factory = create_uuid_factory(WorkingGroup)
_consultation_factory = create_uuid_factory(Consultation)
_person_factory = create_uuid_factory(User)
_meeting_factory = create_uuid_factory(Meeting)
_agenda_item_factory = create_uuid_factory(AgendaItem)
_comment_factory = create_uuid_factory(Comment)


def consultation_factory(request: 'IRequest') -> 'Consultation | Root':
    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _consultation_factory(request)


def working_group_factory(request: 'IRequest') -> 'WorkingGroup | Root':
    return _working_group_factory(request)


def meeting_factory(request: 'IRequest') -> 'Meeting | Root':
    return _meeting_factory(request)


def agenda_item_factory(request: 'IRequest') -> AgendaItem:
    return _agenda_item_factory(request)


def comment_factory(request: 'IRequest') -> Comment:
    return _comment_factory(request)


def default_meeting_factory(request: 'IRequest') -> Meeting:
    factory = create_uuid_factory(Meeting)
    return factory(request)


def person_factory(request: 'IRequest') -> 'User | Root':

    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _person_factory(request)


def general_file_factory(request: 'IRequest') -> GeneralFile:
    factory = create_uuid_factory(GeneralFile)
    return factory(request)
