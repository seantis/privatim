from io import BytesIO
from PIL import Image
from pyramid.httpexceptions import HTTPForbidden, HTTPFound

from privatim.controls.controls import Button
from privatim.i18n import _
from privatim import authenticated_user
from privatim.models.file import GeneralFile


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest
    from privatim.types import RenderData, RenderDataOrRedirectOrForbidden


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


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

    def allowed_file(filename: str) -> bool:
        return (
            '.' in filename
            and filename.rsplit('.', 1)[1].lower()
            in ALLOWED_IMG_EXTENSIONS
        )

    def validate_image(file: BytesIO) -> bool:
        try:
            img = Image.open(file)
            img.verify()
            return True
        except Exception:
            return False

    user = authenticated_user(request)
    target_url = request.route_url('profile')
    if not user:
        return HTTPForbidden()

    if request.method == 'POST':
        # Check if 'profilePic' is in the request.POST
        if 'profilePic' not in request.POST:
            request.messages.add(_('No file uploaded'), 'error')
            return HTTPFound(location=target_url)

        input_file = request.POST['profilePic']

        # Check if the input_file has the necessary attributes
        if not hasattr(input_file, 'file') or not hasattr(
            input_file, 'filename'
        ):
            request.messages.add(_('Invalid file upload'), 'error')
            return HTTPFound(location=target_url)

        # Read the file content
        file_content = input_file.file.read()

        # Validate file size
        file_size = len(file_content)
        if file_size == 0:
            request.messages.add(_('Uploaded file is empty'), 'error')
            return HTTPFound(location=target_url)

        if file_size > MAX_FILE_SIZE:
            request.messages.add(_('File size exceeds 5MB limit'), 'error')
            return HTTPFound(location=target_url)

        # Validate file extension
        if not allowed_file(input_file.filename):
            request.messages.add(
                _('Invalid file type. Allowed types are png, jpg, jpeg, gif'),
                'error',
            )
            return HTTPFound(location=target_url)

        # Validate image content
        if not validate_image(BytesIO(file_content)):
            request.messages.add(_('Invalid image file'), 'error')
            return HTTPFound(location=target_url)

        # If all validations pass, save the file
        user.profile_pic = GeneralFile(
            filename=input_file.filename, content=file_content
        )

        message = _('Successfully updated profile picture')
        request.dbsession.add(user)
        request.messages.add(message, 'success')

    return HTTPFound(location=target_url)
