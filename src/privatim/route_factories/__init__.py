from sqlalchemy import select, exists

from .root_factory import root_factory
from .uuid_factory import create_uuid_factory
from privatim.models import AgendaItem, GeneralFile
from privatim.models.commentable import Comment
from privatim.models import WorkingGroup, Consultation, User, Meeting
from privatim.models.file import SearchableFile


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.orm.abstract import AbstractFile
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


def consultation_from_comment_factory(
    request: 'IRequest',
) -> Consultation | None:
    comment_id = request.matchdict['id']
    session = request.dbsession

    """ This allows us to conveniently link to comments, and we are link to
    the model they appear in instead.

    Note: Currently there is only one model (Consultation) in which we make
    comments. If this changes in the future we'll have to adjust this function.
    """

    # First, get the comment
    comment = session.get(Comment, comment_id)
    if not comment:
        return None

    def get_top_level_comment(comment: Comment) -> Comment:
        while comment.parent:
            comment = comment.parent
        return comment

    # Get the top-level comment
    top_level_comment = get_top_level_comment(comment)

    # Now search for the consultation
    subquery = select(1).where(
        Consultation.comments.any(Comment.id == top_level_comment.id)
    )
    return session.query(Consultation).filter(exists(subquery)).first()


def default_meeting_factory(request: 'IRequest') -> Meeting:
    factory = create_uuid_factory(Meeting)
    return factory(request)


def person_factory(request: 'IRequest') -> 'User | Root':

    if request.matchdict.get('id', None) is None:
        return root_factory(request)

    return _person_factory(request)


def file_factory(request: 'IRequest') -> 'AbstractFile | None':
    file_id = request.matchdict['id']
    dbsession = request.dbsession

    general_file = (
        dbsession.query(GeneralFile).filter(GeneralFile.id == file_id).first()
    )
    if general_file is not None:
        return general_file

    searchable_file = (
        dbsession.query(SearchableFile)
        .filter(SearchableFile.id == file_id)
        .first()
    )
    return searchable_file


def general_file_factory(request: 'IRequest') -> GeneralFile:
    factory = create_uuid_factory(GeneralFile)
    return factory(request)
