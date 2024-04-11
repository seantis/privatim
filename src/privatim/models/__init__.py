from typing import TYPE_CHECKING

from sqlalchemy.orm import configure_mappers

# XXX import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
# https://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/sqlalchemy.html#importing-all-sqlalchemy-models
from privatim.models.consultation import Consultation
from privatim.models.meeting import Meeting
from privatim.models.statement import Statement
from privatim.models.user import Group, User, Person
from privatim.orm import get_engine
from privatim.orm import get_session_factory
from privatim.orm import get_tm_session

if TYPE_CHECKING:
    from pyramid.config import Configurator


# Run ``configure_mappers`` after defining all of the models to ensure
# all relationships can be setup.
configure_mappers()


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


__all__ = (
    'includeme',
    'Group',
    'User',
    'Statement',
    'Meeting',
    'Consultation',
)
