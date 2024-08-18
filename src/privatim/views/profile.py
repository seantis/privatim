from pyramid.httpexceptions import HTTPForbidden, HTTPFound, HTTPClientError

from privatim.controls.controls import Button
from privatim.i18n import _
from privatim import authenticated_user
from privatim.models.file import GeneralFile


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirectOrForbidden


def profile_view(request: 'IRequest') -> 'RenderData':
    user = request.user
    upload_profile_pic = Button(
        title=_('Upload a photo...'),
        description=_('Upload a photo...'),
        icon='upload',
        css_class='dropdown-item',
        id='uploadPhotoLink',
    )
    data_item_title = (
        user.profile_pic.filename
        if user.profile_pic else _('the profile picture')
    )

    delete_profile_pic = Button(
        title=_('Delete photo'),
        url=(
            request.route_url(
                'delete_general_file',
                id=user.picture.id,
                _query={'target_url': 'profile'},
            )
        ),
        description=_('Delete photo'),
        icon='trash',
        data_item_title=data_item_title,
        modal='#delete-xhr',
        css_class='dropdown-item',
        id='deletePhotoLink',
    )
    return {
        'user': user,
        'delete_title': _('Delete photo'),
        'delete_profile_picture_button': delete_profile_pic(),
        'upload_profile_picture_button': upload_profile_pic(),
    }


def add_profile_image_view(
    request: 'IRequest',
) -> 'RenderDataOrRedirectOrForbidden':
    user = authenticated_user(request)
    target_url = request.route_url('profile')
    if not user:
        return HTTPForbidden()

    if request.method == 'POST':
        # input file is this type, but mypy is not lovin it:
        # from cgi import FieldStorage as _cgi_FieldStorage
        input_file = request.POST['profilePic']
        if not all(hasattr(input_file, attr) for attr in ['file', 'filename']):
            return HTTPClientError()

        user.profile_pic = GeneralFile(
            filename=input_file.filename,  # type: ignore
            content=input_file.file  # type: ignore
        )
        message = _('Successfully updated profile picture')
        request.dbsession.add(user)
        request.messages.add(message, 'success')
    return HTTPFound(location=target_url)
