import subprocess  # nosec
from typing import Optional

_git_revision_hash: Optional[str] = None


def get_git_revision_hash() -> Optional[str]:
    global _git_revision_hash
    if _git_revision_hash is None:
        try:
            _git_revision_hash = (
                subprocess.check_output(  # nosec
                    ['/usr/bin/git', 'rev-parse', '--short', 'HEAD'],
                    shell=False,
                    stderr=subprocess.DEVNULL
                )
                .decode('ascii')
                .strip()
            )
        except subprocess.CalledProcessError:
            _git_revision_hash = None
    return _git_revision_hash
