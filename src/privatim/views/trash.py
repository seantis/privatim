from sqlalchemy import select
from privatim.models import (
    Consultation,
    Meeting,
    WorkingGroup,
)
from privatim.i18n import _
from pyramid.httpexceptions import HTTPFound
from typing import TYPE_CHECKING, TypedDict, List, Sequence, Type

if TYPE_CHECKING:
    from privatim.orm import FilteredSession
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirect
    from privatim.models.soft_delete import SoftDeleteMixin

model_map = {
    'consultation': Consultation,
    'working_group': WorkingGroup,
    'meeting': Meeting,
}


class DeletedItemData(TypedDict):
    """ Somewhat generic data structure for deleted items. """
    id: str
    title: str
    restore_url: str
    model_url: str
    item_type: str


def generate_deleted_item_data(
    request: 'IRequest', item: 'SoftDeleteMixin', item_type: str
) -> DeletedItemData:
    assert hasattr(item, 'id') and hasattr(
        item, 'title'
    ), 'Item does not have required attributes.'

    return {
        'id': str(item.id),
        'title': getattr(item, 'title', getattr(item, 'name', '')),
        'model_url': request.route_url(item_type, id=item.id),
        'restore_url': request.route_url(
            'restore_soft_deleted_model', item_type=item_type, item_id=item.id
        ),
        'item_type': item_type,
    }


def trash_view(request: 'IRequest') -> 'RenderData':

    def get_deleted_items(
        session: 'FilteredSession', model: Type['SoftDeleteMixin']
    ) -> Sequence['SoftDeleteMixin']:
        with session.no_soft_delete_filter():
            stmt = select(model).filter(model.deleted.is_(True))
            result = session.execute(stmt)
            deleted_items = result.scalars().all()
        return deleted_items

    session = request.dbsession
    deleted_items: List[DeletedItemData] = []
    deleted_items.extend(
        [
            generate_deleted_item_data(request, item, 'consultation')
            for item in get_deleted_items(session, Consultation)
        ]
    )

    return {
        'title': _('Trash'),
        'items': deleted_items,
    }


def restore_consultation_chain(
        session: 'FilteredSession',
        consultation: Consultation
) -> None:
    """Restore an entire consultation chain starting from any point."""
    # Restore backwards through the chain
    current: Consultation | None = consultation
    while current is not None:
        current.revert_soft_delete()
        session.add(current)
        current = current.previous_version

    # Also restore forwards through the chain
    current = consultation.replaced_by
    while current is not None:
        current.revert_soft_delete()
        session.add(current)
        current = current.replaced_by


def restore_soft_deleted_model_view(
        request: 'IRequest',
) -> 'RenderDataOrRedirect':
    session = request.dbsession
    item_type = request.matchdict['item_type']
    item_id = request.matchdict['item_id']
    model = model_map.get(item_type)

    if not model:
        request.messages.add(_('Invalid item type.'), 'error')
        return HTTPFound(location=request.route_url('trash'))

    target_url = request.route_url('consultation', id=item_id)

    with session.no_soft_delete_filter():
        stmt = select(model).filter_by(id=item_id)
        item = session.execute(stmt).scalar_one_or_none()

        if item:
            if isinstance(item, Consultation):
                restore_consultation_chain(session, item)
            else:
                item.revert_soft_delete()
                session.add(item)

            session.flush()
            session.refresh(item)
            request.messages.add(_('Item restored successfully.'), 'success')
        else:
            request.messages.add(_('Item not found.'), 'error')
            return HTTPFound(location=request.route_url('trash'))

    return HTTPFound(location=target_url)
