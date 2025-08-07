from __future__ import annotations
import subprocess  # nosec

_git_revision_hash: str | None = None


def get_git_revision_hash() -> str | None:
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
