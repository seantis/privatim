from fanstatic import Library
from fanstatic import Resource

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
bootstrap_css = css('custom.css', depends=[bootstrap])

bootstrap_js = js('bootstrap.bundle.min.js')
