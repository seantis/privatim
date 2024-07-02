
from sqlalchemy import event, func
from sqlalchemy.orm import configure_mappers, Mapper

from privatim.i18n import locales
# XXX import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
# https://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/sqlalchemy.html#importing-all-sqlalchemy-models

from privatim.models.group import Group
from privatim.models.group import WorkingGroup
from privatim.models.searchable import SearchableMixin
from privatim.models.user import User
from privatim.models.consultation import Consultation
from privatim.models.meeting import Meeting, AgendaItem
from privatim.models.file import GeneralFile
from privatim.models.consultation import Tag
from privatim.models.statement import Statement
from privatim.models.password_change_token import PasswordChangeToken
from privatim.orm import get_engine, Base
from privatim.orm import get_session_factory
from privatim.orm import get_tm_session


# Prevent linters from complaining about unused imports
Tag
Group
WorkingGroup
User
Consultation
Meeting
AgendaItem
Statement
PasswordChangeToken
GeneralFile
SearchableMixin


from typing import TYPE_CHECKING, Any, TypeVar  # noqa: E402
if TYPE_CHECKING:
    from pyramid.config import Configurator
    from sqlalchemy.engine import Connection

# Run ``configure_mappers`` after defining all of the models to ensure
# all relationships can be setup.
configure_mappers()


def update_searchable_text_listener(
    mapper: Mapper['Any'], connection: 'Connection', target: Any
) -> None:
    return
    # we will implement this for updates of document text
    if connection.engine.name != 'postgresql':
        # todo: fallback if local development uses sqlite?
        raise ValueError('Only PostgreSQL is supported')
    for locale, language in locales.items():
        if hasattr(target, f'searchable_text_{locale}'):
            setattr(
                target,
                f'searchable_text_{locale}',
                func.to_tsvector(language, target.searchable_text),
            )


def register_search_listeners(model: 'type[Consultation | Meeting]') -> None:
    event.listen(model, 'after_insert', update_searchable_text_listener)
    event.listen(model, 'after_update', update_searchable_text_listener)


register_search_listeners(Consultation)


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
