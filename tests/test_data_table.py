import pytest

from datetime import datetime
from operator import itemgetter
from operator import methodcaller
from pyramid.httpexceptions import HTTPOk

from privatim.data_table import AJAXDataTable
from privatim.data_table import DataColumn
from privatim.data_table import DataTable
from privatim.data_table import coerce_int
from privatim.data_table import format_option
from privatim.data_table import maybe_escape
from privatim.testing import DummyRequest


def test_maybe_escape():
    assert maybe_escape(None) == ''
    assert maybe_escape('<') == '&lt;'
    assert maybe_escape('>') == '&gt;'


def test_data_table():
    class TestTable(DataTable):
        test = DataColumn('Test')

        def rows(self):
            return []

    request = DummyRequest()
    table = TestTable(None, request)
    assert table.context is None
    assert table.request == request
    assert table.options == {}


def test_data_table_default_options():
    class TestTable(DataTable):
        default_options = {'paging': False}
        test = DataColumn('Test')

        def rows(self):
            return []

    request = DummyRequest()
    table = TestTable(None, request)
    assert table.context is None
    assert table.request == request
    assert table.options == {'paging': False}
    assert table().startswith(
        '<table class="table data-table" data-paging="false"'
    )

    table = TestTable(None, request, paging=True)
    assert table.context is None
    assert table.request == request
    assert table.options == {'paging': True}
    assert table().startswith(
        '<table class="table data-table" data-paging="true"'
    )


def test_data_table_html(config, user, dummy_org):
    class UserTable(DataTable):
        first_name = DataColumn('Name')

        def rows(self):
            return self.context.users

    session = config.dbsession
    user.first_name = 'Test User'
    session.flush()
    session.refresh(user)

    request = DummyRequest()
    table = UserTable(dummy_org(), request)
    html = table()
    assert html == str(table)
    assert html == table.__html__()
    assert html == (
        '<table class="table data-table" id="usertable">\n'
        '  <thead>\n'
        '    <tr>\n'
        '      <th data-data="first_name" data-name="first_name" scope="col">'
        'Name</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        f'    <tr id="row-{user.id}">\n'
        '      <td >Test User</td>\n'
        '    </tr>\n'
        '  </tbody>\n'
        '</table>\n'
    )


def test_data_table_buttons_html(config, user, dummy_org):
    class UserTable(DataTable):
        first_name = DataColumn('Name')

        def rows(self):
            return self.context.users

        def buttons(self, row=None):
            return ['<button>Dummy</button>']

    session = config.dbsession
    user.first_name = 'Test User'
    session.flush()
    session.refresh(user)

    request = DummyRequest()

    table = UserTable(dummy_org(), request)
    html = table()
    assert html == str(table)
    assert html == table.__html__()
    assert html == (
        '<table class="table data-table" id="usertable">\n'
        '  <thead>\n'
        '    <tr>\n'
        '      <th data-data="first_name" data-name="first_name" scope="col">'
        'Name</th>\n'
        '      <th data-class-name="text-nowrap text-end" data-data="buttons" '
        'data-name="buttons" data-orderable="false" data-searchable="false" '
        'scope="col">'
        '</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        f'    <tr id="row-{user.id}">\n'
        '      <td >Test User</td>\n'
        '      <td class="text-nowrap text-end">\n'
        '        <button>Dummy</button>\n'
        '      </td>\n'
        '    </tr>\n'
        '  </tbody>\n'
        '</table>\n'
    )


def test_ajax_data_table():
    class TestTable(AJAXDataTable):
        test = DataColumn('Test')

        def query(self):
            return []

        # this should never be different from len(query) in production
        # but we use this in testing to check whether the server side
        # processing options only get set if the result set can't fit
        # inside a single request
        def total_records(self):
            return 20

    request = DummyRequest()
    table = TestTable(None, request)
    assert table.context is None
    assert table.request == request
    assert table.options == {
        'server_side': True,
        'defer_render': True,
        'processing': True,
        'ajax': 'http://example.com',
        'defer_loading': 20,
    }
    assert table.draw == -1
    assert table.start == 0
    assert table.length == 10
    assert table.search == ''
    assert table.order_by is None
    assert table.order_dir == 'asc'

    request.GET['draw'] = '1'
    request.GET['start'] = '0'
    request.GET['length'] = '200'
    request.GET['search[value]'] = 'Test'
    request.GET['order[0][column]'] = '0'
    request.GET['order[0][dir]'] = 'desc'
    table = TestTable(None, request)
    # everything fits on one page
    assert table.options == {}
    assert table.draw == 1
    assert table.start == 0
    assert table.length == 200
    assert table.search == 'Test'
    assert table.order_by == 'test'
    assert table.order_dir == 'desc'

    request.GET['draw'] = 'bogus'
    request.GET['start'] = 'bogus'
    request.GET['length'] = 'bogus'
    request.GET['search[value]'] = 'bogus'
    request.GET['order[0][column]'] = 'bogus'
    request.GET['order[0][dir]'] = 'bogus'
    table = TestTable(None, request)
    assert table.draw == -1
    assert table.start == 0
    assert table.length == 10
    assert table.search == 'bogus'
    assert table.order_by is None
    assert table.order_dir == 'asc'


def test_ajax_data_table_xhr_request():
    class TestTable(AJAXDataTable):
        test = DataColumn('Test')

        def query(self):
            return []

        def total_records(self):
            return 0

    request = DummyRequest(is_xhr=True)
    request.GET['draw'] = '1'
    request.GET['start'] = '0'
    request.GET['length'] = '200'
    request.GET['search[value]'] = 'Test'
    request.GET['order[0][column]'] = '0'
    request.GET['order[0][dir]'] = 'desc'
    with pytest.raises(HTTPOk) as exc_info:
        TestTable(None, request)
    response = exc_info.value
    assert response.json['draw'] == 1
    assert response.json['recordsTotal'] == 0
    assert response.json['recordsFiltered'] == 0


def test_ajax_data_table_filtered_records():
    class UserTable(AJAXDataTable):
        first_name = DataColumn('First Name')
        last_name = DataColumn('Last Name')

        def query(self):
            return [
                {'first_name': 'John', 'last_name': 'Doe'},
                {'first_name': 'Jane', 'last_name': 'Doe'},
                {'first_name': 'Anon', 'last_name': 'ymous'},
            ]

        def total_records(self):
            return 3

    request = DummyRequest()
    table = UserTable(None, request, getter=itemgetter)
    assert table.filtered_records() == 3

    request.GET['search[value]'] = 'Doe'
    table = UserTable(None, request, getter=itemgetter)
    assert table.filtered_records() == 2

    request.GET['search[value]'] = 'john DOE'
    table = UserTable(None, request, getter=itemgetter)
    assert table.filtered_records() == 1


def test_ajax_data_table_matches_search():
    class UserTable(AJAXDataTable):
        first_name = DataColumn('First Name')
        last_name = DataColumn('Last Name')

        def query(self):
            return []

        def total_records(self):
            return 0

    request = DummyRequest()
    table = UserTable(None, request, getter=itemgetter)
    row = {'first_name': 'Johnathon', 'last_name': 'Doe'}
    assert table.matches_search(row)

    table.search = 'Doe'
    assert table.matches_search(row)

    table.search = 'doe'
    assert table.matches_search(row)

    table.search = 'DOE'
    assert table.matches_search(row)

    table.search = 'John Doe'
    assert table.matches_search(row)

    table.search = 'Johnathon Doe'
    assert table.matches_search(row)

    table.search = 'Johnny Doe'
    assert not table.matches_search(row)

    table.search = 'Johnny'
    assert not table.matches_search(row)

    table.search = 'bogus'
    assert not table.matches_search(row)


def test_ajax_data_table_rows_search():
    class UserTable(AJAXDataTable):
        first_name = DataColumn('First Name')
        last_name = DataColumn('Last Name')

        def query(self):
            return [
                {'first_name': 'John', 'last_name': 'Doe'},
                {'first_name': 'Jane', 'last_name': 'Doe'},
                {'first_name': 'Anon', 'last_name': 'ymous'},
            ]

        def total_records(self):
            return 3

    request = DummyRequest()
    table = UserTable(None, request, getter=itemgetter)
    assert len(table.rows()) == 3
    assert table._filtered_records == 3

    request.GET['search[value]'] = 'Doe'
    table = UserTable(None, request, getter=itemgetter)
    assert table.rows() == [
        {'first_name': 'John', 'last_name': 'Doe'},
        {'first_name': 'Jane', 'last_name': 'Doe'},
    ]
    assert table._filtered_records == 2

    request.GET['search[value]'] = 'john DOE'
    table = UserTable(None, request, getter=itemgetter)
    assert table.rows() == [
        {'first_name': 'John', 'last_name': 'Doe'},
    ]
    assert table._filtered_records == 1


def test_ajax_data_table_rows_limit():
    class UserTable(AJAXDataTable):
        first_name = DataColumn('First Name')
        last_name = DataColumn('Last Name')

        def query(self):
            return [
                {'first_name': 'John', 'last_name': 'Doe'},
                {'first_name': 'Jane', 'last_name': 'Doe'},
                {'first_name': 'Anon', 'last_name': 'ymous'},
            ]

        def total_records(self):
            return 3

    request = DummyRequest()
    table = UserTable(None, request, getter=itemgetter)
    assert len(table.rows()) == 3
    assert table._filtered_records == 3

    request.GET['length'] = '2'
    table = UserTable(None, request, getter=itemgetter)
    assert table.rows() == [
        {'first_name': 'John', 'last_name': 'Doe'},
        {'first_name': 'Jane', 'last_name': 'Doe'},
    ]
    assert table._filtered_records == 3

    request.GET['start'] = '1'
    table = UserTable(None, request, getter=itemgetter)
    assert table.rows() == [
        {'first_name': 'Jane', 'last_name': 'Doe'},
        {'first_name': 'Anon', 'last_name': 'ymous'},
    ]
    assert table._filtered_records == 3


def test_ajax_data_table_data(config, user, dummy_org):
    class UserTable(AJAXDataTable):
        first_name = DataColumn('Name')

        def query(self):
            return self.context.users

        def total_records(self):
            return 12

    session = config.dbsession
    user.first_name = 'Test User'
    session.flush()
    session.refresh(user)

    request = DummyRequest()
    request.GET['draw'] = 15
    table = UserTable(dummy_org(), request)
    data = table.data()
    assert data['draw'] == 15
    assert data['recordsTotal'] == 12
    assert data['recordsFiltered'] == 1
    assert data['data'] == [{
        'DT_RowId': f'row-{user.id}',
        'first_name': 'Test User'
    }]


def test_ajax_data_table_data_buttons(config, user, dummy_org):
    class UserTable(AJAXDataTable):
        first_name = DataColumn('Name')

        def query(self):
            return self.context.users

        def total_records(self):
            return 12

        def buttons(self, row=None):
            return ['<button>Dummy</button>']

    session = config.dbsession
    user.first_name = 'Test User'
    session.flush()
    session.refresh(user)

    request = DummyRequest()
    request.GET['draw'] = 15
    table = UserTable(dummy_org(), request)
    data = table.data()
    assert data['draw'] == 15
    assert data['recordsTotal'] == 12
    assert data['recordsFiltered'] == 1
    assert data['data'] == [{
        'DT_RowId': f'row-{user.id}',
        'first_name': 'Test User',
        'buttons': '<button>Dummy</button>'
    }]


def test_data_column():
    column = DataColumn('Test')
    assert column.name == ''
    assert column.title == 'Test'
    assert column.description == ''
    assert column.options == {}
    assert column.format_data == maybe_escape
    assert column.sort_key is None


def test_data_column_name():
    column = DataColumn('Test', name='test')
    assert column.name == 'test'

    column.name = 'test2'
    assert column.name == 'test2'


def test_data_column_name_implicit():
    class TestTable(DataTable):
        test = DataColumn('Test')
    assert TestTable.test.name == 'test'

    TestTable.test.name = 'test2'
    assert TestTable.test.name == 'test2'


def test_data_column_name_explicit_over_implicit():
    class TestTable(DataTable):
        test = DataColumn('Test', name='test2')
    assert TestTable.test.name == 'test2'


def test_data_column_data():
    column = DataColumn('Test')
    assert column.data('test') == 'test'
    assert column.data('<markup>') == '&lt;markup&gt;'


def test_data_column_data_format_data():
    column = DataColumn('Test', format_data=lambda d: 'true' if d else 'false')
    assert column.data(True) == 'true'
    assert column.data(False) == 'false'


def test_data_column_data_sort_key():
    date = datetime(2018, 10, 10, 10, 10, 10)
    column = DataColumn(
        'Test',
        format_data=methodcaller('isoformat'),
        sort_key=methodcaller('timestamp')
    )
    assert column.data(date) == {
        'display': '2018-10-10T10:10:10',
        '@data-order': date.timestamp()
    }


def test_data_column_header():
    column = DataColumn('Test')
    assert column.header() == '<th scope="col">Test</th>'

    column = DataColumn('Test', name='test')
    assert column.header() == (
        '<th data-data="test" data-name="test" scope="col">Test</th>'
    )

    column = DataColumn('Test', 'Detailed')
    assert column.header() == (
        '<th data-bs-toggle="tooltip" scope="col" title="Detailed">Test</th>'
    )

    column = DataColumn('Test', class_name='text-end')
    assert column.header() == (
        '<th class="text-end" data-class-name="text-end" scope="col">Test</th>'
    )

    column = DataColumn('Test', orderable=False)
    assert column.header() == (
        '<th data-orderable="false" scope="col">Test</th>'
    )


def test_data_column_cell():
    column = DataColumn('Test')
    assert column.cell('test') == '<td >test</td>'
    assert column.cell('<markup>') == '<td >&lt;markup&gt;</td>'


def test_data_column_cell_class_name():
    column = DataColumn('Test', class_name='text-end')
    assert column.cell('test') == '<td class="text-end">test</td>'


def test_data_column_cell_format_data():
    column = DataColumn('Test', format_data=lambda d: 'true' if d else 'false')
    assert column.cell(True) == '<td >true</td>'
    assert column.cell(False) == '<td >false</td>'


def test_data_column_cell_sort_key():
    date = datetime(2018, 10, 10, 10, 10, 10)
    column = DataColumn(
        'Test',
        format_data=methodcaller('isoformat'),
        sort_key=methodcaller('timestamp')
    )
    assert column.cell(date) == (
        f'<td data-order="{date.timestamp()}">2018-10-10T10:10:10</td>'
    )


def test_coerce_int():
    assert coerce_int(1) == 1
    assert coerce_int(1.0) == 1
    assert coerce_int('1') == 1
    assert coerce_int('bogus') == -1
    assert coerce_int(None) == -1
    assert coerce_int(object()) == -1


def test_format_option():
    assert format_option(None) == 'null'
    assert format_option(True) == 'true'
    assert format_option(False) == 'false'
    assert format_option(1) == '1'
    assert format_option(1.5) == '1.5'
    assert format_option('test') == 'test'
    assert format_option([1, 2, 3]) == '[1,2,3]'
    assert format_option({'key': 'value'}) == '{"key":"value"}'
