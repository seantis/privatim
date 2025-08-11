import logging
from sqlalchemy.orm import configure_mappers

# XXX import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
# https://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/sqlalchemy.html#importing-all-sqlalchemy-models

from privatim.models.group import Group
from privatim.models.group import WorkingGroup
from privatim.models.searchable import SearchableMixin
from privatim.models.user import User
from privatim.models.consultation import Consultation
from privatim.models.comment import Comment
from privatim.models.meeting import Meeting, AgendaItem, MeetingEditEvent
from privatim.models.association_tables import (
    MeetingUserAttendance,
    AgendaItemDisplayState,
    AgendaItemStatePreference,
)
from privatim.models.file import GeneralFile, SearchableFile
from privatim.models.password_change_token import PasswordChangeToken
from privatim.models.tan import TAN
from privatim.orm import get_engine
from privatim.orm import get_session_factory
from privatim.orm import get_tm_session


# Prevent linters from complaining about unused imports

Group
WorkingGroup
User
Consultation
Comment
Meeting
MeetingEditEvent
MeetingUserAttendance
AgendaItemDisplayState
AgendaItemStatePreference
AgendaItem
PasswordChangeToken
GeneralFile
SearchableFile
SearchableMixin
TAN


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from pyramid.config import Configurator


logger = logging.getLogger(__name__)


def includeme(config: 'Configurator') -> None:
    """
    Initialize the model for a Pyramid app.

    Activate this setup using ``config.include('privatim.models')``.

    """
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include('pyramid_tm')

    # use pyramid_retry to retry a request when transient exceptions occur
    config.include('pyramid_retry')

    session_factory = get_session_factory(get_engine(settings))
    config.registry['dbsession_factory'] = session_factory  # type:ignore

    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        # r.tm is the transaction manager used by pyramid_tm
        lambda r: get_tm_session(session_factory, r.tm),
        'dbsession',
        reify=True
    )


configure_mappers()
