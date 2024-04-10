from fanstatic import Library
from fanstatic import Resource

js_library = Library('privatim:js', 'js')
css_library = Library('privatim:css', 'css')


def js(*args, **kwargs):
    return Resource(js_library, *args, **kwargs)


def css(*args, **kwargs):
    return Resource(css_library, *args, **kwargs)


bootstrap = css('bootstrap.min.css')
bootstrap_css = css('custom.css', depends=[bootstrap])

bootstrap_js = js('bootstrap.bundle.min.js')
