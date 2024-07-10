"""
Setup static file storage.
"""
from pathlib import Path
from typing import Any

from libcloud.storage.drivers.local import LocalStorageDriver
from sqlalchemy_file.storage import StorageManager


def setup_filestorage(settings: Any) -> None:
    """
    Configure storage of static assets
    """
    documents_dir = Path(settings.get('documents_dir', 'uploads'))
    asset_dir = documents_dir / 'assets'
    asset_dir.mkdir(exist_ok=True, parents=True)

    if 'default' not in StorageManager._storages:

        container = (
            LocalStorageDriver(documents_dir)
            .get_container(asset_dir.name)
        )
        StorageManager.add_storage("default", container)
