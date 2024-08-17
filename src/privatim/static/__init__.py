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

comments_css = css('comments.css')
profile_css = css('profile.css')

jquery = js('jquery.min.js')
bootstrap_core = js('bootstrap.bundle.min.js')
bootstrap_js = js(
    'bootstrap_custom.js',
    depends=[jquery, bootstrap_core]
)

sortable_custom = js('custom/sortable_custom.js', depends=[jquery],
                     renderer=render_js_module)

custom_js = js('custom/custom.js', depends=[jquery])

tom_select_css = css('tom-select.min.css')
tom_select = js('tom_select.complete.min.js')

init_tiptap_editor = js(
    'init_tiptap_editor.js',
    renderer=render_js_module,
)
