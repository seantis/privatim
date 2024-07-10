import logging
from contextlib import contextmanager
from threading import Lock

from sqlalchemy import event

from sqlalchemy.orm import configure_mappers, Session, object_session

from privatim.models.associated_file import SearchableAssociatedFiles

# XXX import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
# https://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/database/sqlalchemy.html#importing-all-sqlalchemy-models

from privatim.models.group import Group
from privatim.models.group import WorkingGroup
from privatim.models.searchable import SearchableMixin
from privatim.models.user import User
from privatim.models.consultation import Consultation
from privatim.models.meeting import Meeting, AgendaItem
from privatim.models.file import GeneralFile, SearchableFile
from privatim.models.statement import Statement
from privatim.models.consultation import Tag
from privatim.models.password_change_token import PasswordChangeToken
from privatim.orm import get_engine
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


from typing import TYPE_CHECKING, Generator  # noqa: E402
if TYPE_CHECKING:
    from pyramid.config import Configurator
    from sqlalchemy.orm import Mapper
    from sqlalchemy.engine import Connection


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


# def update_fulltext_search_text(
#     mapper: 'Mapper[SearchableAssociatedFiles]',
#     connection: 'Connection',
#     target: SearchableAssociatedFiles,
# ) -> None:
#     """
#     Event listener for the 'files' relationship. Triggers a full reindex
#     if any file changes.
#
#     While potentially inefficient for large collections, it's typically
#     fine as the number of files is expected to be small (1-5). Consider
#     optimizing if performance issues arise.
#     """
#     for locale in locales:
#         if hasattr(target, f'searchable_text_{locale}'):
#             target.reindex_files()
#
#
# def register_search_listeners(
#     model: 'type[SearchableAssociatedFiles]',
# ) -> None:
#     event.listen(model, 'after_insert', update_fulltext_search_text)
#     event.listen(
#         model,
#         'after_update',
#         update_fulltext_search_text,
#     )
#     event.listen(
#         model,
#         'after_delete',  # for edit form as well as delete
#         update_fulltext_search_text,
#     )


# def reindex_models_with_searchable_files() -> None:
#
#     seen = set()
#     for _ in Base.metadata.tables.values():
#         for mapper in Base.registry.mappers:
#             cls = mapper.class_
#             if issubclass(cls, SearchableAssociatedFiles):
#                 if cls not in seen:
#                     register_search_listeners(cls)
#                 seen.add(cls)


# class ReindexTracker:
#     def __init__(self) -> None:
#         self.to_reindex: set[SearchableAssociatedFiles] = set()
#         self._lock = Lock()
#
#     @contextmanager
#     def tracking(self) -> Generator[None, None, None]:
#         with self._lock:
#             try:
#                 yield
#             finally:
#                 self.reindex_all()
#
#     def add(self, instance: SearchableAssociatedFiles) -> None:
#         with self._lock:
#             self.to_reindex.add(instance)
#
#     def clear(self) -> None:
#         with self._lock:
#             self.to_reindex.clear()
#
#     def reindex_all(self) -> None:
#         with self._lock:
#             for instance in self.to_reindex:
#                 instance.reindex_files()
#             self.clear()
#
#
# reindex_tracker = ReindexTracker()
#
#
# def searchable_file_change_listener(
#     mapper: 'Mapper[SearchableFile]',
#     connection: 'Connection',
#     target: SearchableFile,
# ) -> None:
#     session = object_session(target)
#     if session is None:
#         return  # The instance is not associated with a session
#
#     logger.debug(f"Change detected for SearchableFile: {target.filename}")
#     try:
#         for link in target.links:
#             if isinstance(link, SearchableAssociatedFiles):
#                 logger.debug(f"Adding instance {link.id} to reindex tracker")
#                 reindex_tracker.add(link)
#     except Exception as e:
#         logger.exception(
#             f"Error processing links for SearchableFile {target.id}: {str(e)}"
#         )
#
#
# def before_commit_listener(session: Session) -> None:
#     reindex_tracker.reindex_all()
#
#
# def setup_reindex_tracking() -> None:
#     event.listen(
#         SearchableFile, 'after_insert', searchable_file_change_listener
#     )
#     event.listen(Session, 'before_commit', before_commit_listener)
#
#
#
# setup_reindex_tracking()

configure_mappers()
