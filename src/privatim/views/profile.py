from pyramid.httpexceptions import HTTPForbidden, HTTPFound, HTTPClientError

from controls.controls import Button
from privatim.i18n import _
from privatim import authenticated_user
from privatim.models import GeneralFile


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
        id='uploadPhotoLink'
    )
    delete_profile_pic_url = request.route_url(
        'delete_general_file',
        id=user.picture.id,
        _query={'target_url': 'profile'},
    )
    delete_profile_pic = Button(
        title=_('Delete photo'),
        url=delete_profile_pic_url,
        description=_('Delete photo'),
        icon='trash',
        data_item_title='test',
        css_class='dropdown-item',
        id='deletePhotoLink'
    )
    return {
        'user': user,
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


def user_pic_url(request: 'IRequest') -> str:
    user = request.user
    return request.route_url('download_general_file', id=user.picture.id)
