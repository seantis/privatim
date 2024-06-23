from privatim.static import get_default_profile_pic_data
from sqlalchemy import select


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from privatim.models import GeneralFile


def get_or_create_default_profile_pic(session: 'Session') -> 'GeneralFile':
    from privatim.models import GeneralFile
    stmt = select(GeneralFile).where(
        GeneralFile.filename == 'default_profile_picture.png'
    )
    default_profile_picture = session.execute(stmt).scalar_one_or_none()
    if default_profile_picture is None:
        filename, data = get_default_profile_pic_data()
        default_profile_picture = GeneralFile(filename=filename, content=data)
        session.add(default_profile_picture)
        session.flush()
        session.refresh(default_profile_picture)
    return default_profile_picture
