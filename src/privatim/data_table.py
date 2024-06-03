import json

from operator import attrgetter
from markupsafe import escape
from pyramid.httpexceptions import HTTPOk
from wtforms.widgets import html_params

from privatim.i18n import translate
from privatim.static import datatable_css
from privatim.static import datatable_js


from typing import Any
from typing import ClassVar
from typing import Generic
from typing import Literal
from typing import TypeVar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pyramid.interfaces import IRequest
    from privatim.types import Callback
    from controls.controls import Button

    Getter = Callable[[str], Callable[['RT'], Any]]
    # NOTE: We are more lenient to support functions such as len
    DataFormatter = Callable[[Any], str | int | float]
    SortKeyCallable = Callable[[Any], Any]

RT = TypeVar('RT')  # RowType


def maybe_escape(value: str | None) -> str:
    if value is None:
        return ''
    return escape(value)


class DataColumn:
    """
    Utility class to encapsulate DataTables column features.
    Refer to https://datatables.net/reference/option/ for possible options.
    Use snake case for naming, i.e. `deferRender` becomes `defer_render`.
    """

    _order:      int = 0  # used to ensure columns are ordered
    title:       str
    description: str
    options:     dict[str, Any]

    def __init__(
        self,
        title:       str,
        description: str = '',
        format_data: 'DataFormatter' = maybe_escape,
        sort_key:    'SortKeyCallable | None' = None,
        condition:   'Callback[bool] | None' = None,
        **options:   Any
    ):

        self.title = title
        self.description = description
        self.format_data = format_data
        self.sort_key = sort_key
        self.options = options
        self._condition = condition

        DataColumn._order += 1
        self._order = DataColumn._order

    def __set_name__(self, owner: type['DataTable[Any]'], name: str) -> None:
        self.options.setdefault('name', name)

    def active(self, context: Any, request: 'IRequest') -> bool:
        if callable(self._condition):
            return self._condition(context, request)
        return True

    @property
    def name(self) -> str:
        return self.options.get('name', '')

    @name.setter
    def name(self, value: str) -> None:
        self.options['name'] = value

    def data(self, data: Any) -> str | dict[str, str]:
        display = str(self.format_data(data))
        if callable(self.sort_key):
            return {'display': display, '@data-order': self.sort_key(data)}
        else:
            return display

    def header(self) -> str:
        params = {'scope': 'col'}
        if 'class_name' in self.options:
            params['class'] = self.options['class_name']
        if self.description:
            params['title'] = translate(self.description)
            params['data-bs-toggle'] = 'tooltip'
        for name, option in self.options.items():
            params[f'data_{name}'] = format_option(option)
        if self.name and 'data_data' not in params:
            # ensure data is set to name if not specified otherwise
            if callable(self.sort_key):
                # we use the same format as the internal representation
                # but we still have to specify the full layout
                data_src = (
                    f'{{"_":"{self.name}.display",'
                    f'"sort":"{self.name}.@data-order"}}'
                )
            else:
                data_src = self.name
            params['data_data'] = data_src
        return f'<th {html_params(**params)}>{translate(self.title)}</th>'

    def cell(self, data: Any) -> str:
        params = {}
        if 'class_name' in self.options:
            params['class'] = self.options['class_name']
        if callable(self.sort_key):
            params['data_order'] = self.sort_key(data)
        return f'<td {html_params(**params)}>{self.format_data(data)}</td>'


def coerce_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_option(option: Any) -> str:
    if option is None:
        return 'null'
    elif isinstance(option, bool):
        return 'true' if option else 'false'
    elif isinstance(option, (int, float, str)):
        return str(option)
    else:
        return json.dumps(option, separators=(',', ':'))


class DataTableMeta(type):
    """
    This meta class ensures that we keep track of all the columns in our
    class without needing to traverse all the attributes each time. We
    compute _all_columns the first time a class gets instantiated.
    """
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if not hasattr(cls, '_all_columns'):
            cls._all_columns = sorted(
                (
                    c for name in dir(cls)
                    if isinstance((c := getattr(cls, name, None)), DataColumn)
                ),
                key=attrgetter('_order')
            )
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name: str, value: object) -> None:
        if isinstance(value, DataColumn) and hasattr(cls, '_all_columns'):
            delattr(cls, '_all_columns')
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name: str) -> None:
        if isinstance(getattr(cls, name, None), DataColumn):
            delattr(cls, '_all_columns')
        type.__delattr__(cls, name)


class DataTable(Generic[RT], metaclass=DataTableMeta):
    """
    Utility class to encapsulate DataTables features.
    Refer to https://datatables.net/reference/option/ for possible options.
    Use snake case for naming, i.e. `deferRender` becomes `defer_render`.
    """
    default_options: ClassVar[dict[str, Any]] = {}
    _all_columns:    ClassVar[list[DataColumn]]
    columns:         list[DataColumn]
    context:         Any
    request:         'IRequest'
    id:              str
    options:         dict[str, Any]

    def __init__(
        self,
        context:   Any,
        request:   'IRequest',
        getter:    'Getter[RT]' = attrgetter,
        id:        str | None = None,
        **options: Any
    ) -> None:

        self.context = context
        self.request = request

        if id is None:
            id = self.__class__.__name__.lower()
        self.id = id

        # filter visible columns
        self.columns = [
            c for c in self._all_columns
            if c.active(self.context, self.request)
        ]

        self._get = getter
        self.options = self.default_options.copy()
        locale = request.locale_name
        if locale != 'en':
            url = self.request.static_url(
                f'privatim:static/json/dataTables.{locale}.json'
            )
            self.options.setdefault('language', {}).setdefault('url', url)
        self.options.update(options)

        datatable_css.need()
        datatable_js.need()

    def rows(self) -> list[RT]:
        raise NotImplementedError

    def buttons(self, row: RT | None = None) -> list['Button']:
        return NotImplemented

    def cell(self, column: DataColumn, row: RT) -> str:
        cell_data = self._get(column.name)(row)
        return column.cell(cell_data)

    def __call__(self) -> str:
        has_buttons = self.buttons() is not NotImplemented
        params = {'id': self.id, 'class': 'table data-table'}
        for name, option in self.options.items():
            params[f'data_{name}'] = format_option(option)
        html = f'<table {html_params(**params)}>\n'
        html += '  <thead>\n'
        html += '    <tr>\n'
        for column in self.columns:
            html += f'      {column.header()}\n'
        if has_buttons:
            th_params = html_params(
                data_class_name='text-nowrap text-end',
                data_data='buttons',
                data_name='buttons',
                data_orderable='false',
                data_searchable='false',
                scope='col',
            )
            html += f'      <th {th_params}></th>\n'
        html += '    </tr>\n'
        html += '  </thead>\n'
        html += '  <tbody>\n'
        for row in self.rows():
            row_id = self._get('id')(row)
            html += f'    <tr id="row-{row_id}">\n'
            for column in self.columns:
                html += f'      {self.cell(column, row)}\n'
            if has_buttons:
                html += '      <td class="text-nowrap text-end">\n'
                for button in self.buttons(row):
                    html += f'        {button}\n'
                html += '      </td>\n'
            html += '    </tr>\n'
        html += '  </tbody>\n'
        html += '</table>\n'
        return html

    def __str__(self) -> str:
        return self.__call__()

    def __html__(self) -> str:
        return self.__call__()


class AJAXDataTable(DataTable[RT]):
    """
    Server side scripting ready version of DataTable.
    """

    _filtered_records: int
    order_dir: Literal['asc', 'desc']

    def __init__(self, context: Any, request: 'IRequest', **options: Any):
        super().__init__(context, request, **options)

        # Read basic filter params
        # NOTE: We do not support multi column sorting or column search terms
        #       but these features have to be explicitly enabled anyways.
        self.draw = coerce_int(self.request.GET.get('draw'))
        self.start = coerce_int(self.request.GET.get('start'))
        if self.start < 0:
            self.start = 0
        default_len = 10
        length_menu = self.options.get('length_menu', None)
        if isinstance(length_menu, list):
            if isinstance(length_menu[0], list):
                length_menu = length_menu[0]
            default_len = length_menu[0]
        default_len = self.options.get('page_length', default_len)
        assert isinstance(default_len, int)
        self.length = coerce_int(self.request.GET.get('length'), default_len)
        self.search = self.request.GET.get('search[value]', '')
        self.order_by = None
        order_by_index = coerce_int(self.request.GET.get('order[0][column]'))
        if 0 <= order_by_index < len(self.columns):
            self.order_by = self.columns[order_by_index].name

        order_dir = self.request.GET.get('order[0][dir]')
        if order_dir == 'desc':
            self.order_dir = 'desc'
        else:
            self.order_dir = 'asc'

        if request.is_xhr:
            raise HTTPOk(json=self.data())

        # we only turn on server side rendering if there is more than one page
        total_records = self.total_records()
        if self.start > 0 or (0 <= self.length < total_records):
            self.options['server_side'] = True
            self.options.setdefault('defer_render', True)
            self.options.setdefault('processing', True)
            self.options.setdefault('ajax', self.request.path_url)
            self.options['defer_loading'] = self.total_records()

    def total_records(self) -> int:
        raise NotImplementedError

    def query(self) -> 'Iterable[RT]':
        raise NotImplementedError

    def filtered_records(self) -> int:
        if not hasattr(self, '_filtered_records'):
            # NOTE: rows() populates this attribute
            self.rows()
        return self._filtered_records

    def matches_search(self, row: RT) -> bool:
        terms = self.search.split()
        for term in terms:
            term = str(escape(term)).lower()
            found = False
            for column in self.columns:
                cell_data = self._get(column.name)(row)
                formatted = str(column.format_data(cell_data))
                if term in formatted.lower():
                    found = True
                    break
            if not found:
                return False
        return True

    def rows(self) -> list[RT]:
        if not hasattr(self, '_rows'):
            rows = []
            filtered_records = 0
            query = self.query()
            for row in query:
                if self.search and not self.matches_search(row):
                    continue
                filtered_records += 1
                if self.length > 0:
                    # only apply limit if length is set
                    if self.start >= filtered_records:
                        continue
                    if self.start+self.length < filtered_records:
                        continue
                rows.append(row)
            self._rows = rows
            self._filtered_records = filtered_records
        return self._rows

    def data(self) -> dict[str, Any]:
        has_buttons = self.buttons() is not NotImplemented
        data = []
        for row in self.rows():
            column_data: dict[str, Any]
            row_id = self._get('id')(row)
            column_data = {'DT_RowId': f'row-{row_id}'}
            for column in self.columns:
                cell_data = getattr(row, column.name)
                column_data[column.name] = column.data(cell_data)
            if has_buttons:
                buttons = self.buttons(row)
                column_data['buttons'] = ' '.join(str(b) for b in buttons)
            data.append(column_data)
        return {
            'draw': self.draw,
            'recordsTotal': self.total_records(),
            'recordsFiltered': self.filtered_records(),
            'data': data,
        }
