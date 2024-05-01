import re
from functools import cached_property
from pyquery import PyQuery as pq
from webtest import TestApp

from tests.shared.utils import find_login_form

EXTRACT_HREF = re.compile(
    r'(?:href|ic-get-from|ic-post-to|ic-delete-from)="([^"]+)')


class Client(TestApp):
    """ A condensed (minimalist) version of the `client`, derived from onegov.
    """

    def spawn(self):
        """ Spawns a new client that points to the same app.

        All login data / cookies are lost.

        """

        return self.__class__(self.app)

    def login(self, username, password):
        url = '/login'
        login_page = self.get(url)
        form = find_login_form(login_page.forms)
        form.set('username', username)
        form.set('password', password)
        return login_page.form.submit()

    def login_admin(self, to=None):
        return self.login('admin@example.org', 'test', to)

    def logout(self):
        raise NotImplementedError("This method is not implemented yet.")

    def extract_href(self, link):
        """ Takes a link (<a href...>) and returns the href address. """

        result = EXTRACT_HREF.search(link)
        return result and result.group(1) or None

    def extend_response(self, response):
        """ Takes the default response and adds additional methods/properties,
        or overrides them.

        """
        bases = [GenericResponseExtension]
        bases.append(response.__class__)
        response.__class__ = type('ExtendedResponse', tuple(bases), {})

        return response

    def do_request(self, *args, **kwargs):
        """ Dirtily inject extra methods into the response -> done this way
        because not all testclients support overriding the response class
        (i.e. webtest-selenium).

        """

        return self.extend_response(super().do_request(*args, **kwargs))


class GenericResponseExtension:

    def select_checkbox(self, groupname, label, form=None, checked=True):
        """ Selects one of many checkboxes by fuzzy searching the label next to
        it. Webtest is not good enough in this regard.

        Selects the checkbox from the form returned by page.form, or the given
        form if passed. In any case, the form needs to be part of the page.

        """

        elements = self.pyquery(f'input[name="{groupname}"]')

        if not elements:
            raise KeyError(f"No input named {groupname} found")

        form = form or self.form

        for ix, el in enumerate(elements):
            if label in el.label.text_content():
                form.get(groupname, index=ix).value = checked

    def select_radio(self, groupname, label, form=None):
        """ Like `select_checkbox`, but with the ability to select a radio
        button by the name of its label.

        """

        elements = self.pyquery(f'input[name="{groupname}"]')

        if not elements:
            raise KeyError(f"No input named {groupname} found")

        form = form or self.form

        for el in elements:
            if label in el.label.text_content():
                form.get(groupname).value = el.values()[-1]
                break

    @cached_property
    def pyquery(self):
        """ Webtests property of the same name seems to not work on all
        pages (it uses self.testbody and not self.body) and it also doesn't
        cache the result, which is an easy way to improve some lookups here.

        """
        return pq(self.body)

    def __or__(self, text):
        """ Grep style searching the response, e.g.
        `print(client.get('/') | 'Text')`

        """
        return '\n'.join([l for l in str(self).split('\n') if text in l])
