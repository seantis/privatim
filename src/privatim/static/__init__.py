from fanstatic import Library
from fanstatic import Resource

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Iterable
    from fanstatic.core import Dependable


js_library = Library('privatim:js', 'js')
css_library = Library('privatim:css', 'css')


def js(
        relpath:    str,
        depends:    'Iterable[Dependable] | None' = None,
        supersedes: list[Resource] | None = None,
        bottom:     bool = False,
) -> Resource:

    return Resource(
        js_library,
        relpath,
        depends=depends,
        supersedes=supersedes,
        bottom=bottom,
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


fontawesome_css = css('fontawesome.min.css')
bootstrap = css('bootstrap.min.css')
bootstrap_css = css('custom.css', depends=[fontawesome_css, bootstrap])
datatable_css = css('dataTables.bootstrap5.min.css', depends=[bootstrap])

jquery = js('jquery.min.js')
datatable_core = js('jquery.dataTables.min.js', depends=[jquery])
bootstrap_core = js('bootstrap.bundle.min.js')
bootstrap_js = js('bootstrap_custom.js', depends=[jquery, bootstrap_core])
datatable_bootstrap = js(
    'dataTables.bootstrap5.min.js', depends=[bootstrap_core, datatable_core]
)
datatable_js = js('datatables_custom.js', depends=[datatable_bootstrap])
xhr_edit_js = js('xhr_edit.js', depends=[datatable_js])

tom_select_css = css('tom-select.min.css')
tom_select = js('tom-select.complete.min.js')
init_tom_select = js('init-tom-select.js', depends=[tom_select])
