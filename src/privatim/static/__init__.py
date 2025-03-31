from functools import lru_cache
from pathlib import Path
from fanstatic import Library
from fanstatic import Resource
from fanstatic.core import render_js as render_js_default


from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from collections.abc import Iterable
    from fanstatic.core import Dependable

js_library = Library('privatim:js', 'js')
css_library = Library('privatim:css', 'css')


def render_js_module(url: str) -> str:
    return f'<script type="module" src="{url}"></script>'


def js(
        relpath: str,
        depends: 'Iterable[Dependable] | None' = None,
        supersedes: list[Resource] | None = None,
        bottom: bool = False,
        renderer: Callable[[str], str] = render_js_default  # "text/javascript"
) -> Resource:

    return Resource(
        js_library,
        relpath,
        depends=depends,
        supersedes=supersedes,
        bottom=bottom,
        renderer=renderer
    )


def css(
        relpath:    str,
        depends:    'Iterable[Dependable] | None' = None,
        supersedes: list[Resource] | None = None,
        bottom:     bool = False,
) -> Resource:

    return Resource(
        css_library,
        relpath,
        depends=depends,
        supersedes=supersedes,
        bottom=bottom,
    )


@lru_cache(maxsize=1)
def get_default_profile_pic_data() -> tuple[str, bytes]:
    filename = 'default_profile_icon.png'
    default_profile_icon = Path(__file__).parent / filename
    with open(default_profile_icon, 'rb') as file:
        return filename, file.read()


fontawesome_css = css('fontawesome.min.css')
bootstrap = css('bootstrap.min.css')
bootstrap_css = css('custom.css', depends=[fontawesome_css, bootstrap])

profile_css = css('profile.css')

jquery = js('jquery.min.js')
bootstrap_core = js('bootstrap.bundle.min.js')
bootstrap_js = js(
    'bootstrap_custom.js',
    depends=[jquery, bootstrap_core]
)

sortable_custom = js('custom/sortable_custom.js', depends=[jquery],
                     renderer=render_js_module)


tom_select_css = css('tom-select.min.css')
tom_select_js = js('tom_select.complete.min.js')
init_tom_select_js = js('init-tom-select.js')

custom_js = js('custom/custom.js', depends=[jquery])

bundle_js = js('tiptap.bundle.min.js')
init_tiptap_editor = js(
    'tiptap/tiptap.init.js',
    depends=[bundle_js],
)
