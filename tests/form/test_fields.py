import tempfile
from copy import deepcopy
from cgi import FieldStorage
from privatim.forms.fields import UploadMultipleField
from privatim.utils import dictionary_to_binary
from wtforms.form import Form


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


def create_file(mimetype, filename, content):
    fs = FieldStorage()
    fs.file = tempfile.TemporaryFile("wb+")
    fs.type = mimetype
    fs.filename = filename
    fs.file.write(content)
    fs.file.seek(0)
    return fs


class MockField:

    def __init__(self, type, data, choices=None):
        self.type = type
        self.data = data
        self.render_kw = None

        if choices is not None:
            self.choices = choices
        else:
            if isinstance(data, str):
                self.choices = [(data, data)]
            elif isinstance(data, list):
                self.choices = [(c, c) for c in data]


def test_upload_multiple_field():
    def create_field():
        form = Form()
        field = UploadMultipleField()
        field = field.bind(form, 'uploads')
        return form, field

    # Test rendering and initial submit
    form, field = create_field()
    field.process(None)
    assert len(field) == 0

    html = field()
    assert 'without-data' in html
    assert 'multiple' in html
    assert 'name="uploads"' in html
    assert 'with-data' not in html
    assert 'name="uploads-0"' not in html

    file1 = create_file('text/plain', 'baz.txt', b'baz')
    file2 = create_file('text/plain', 'foobar.txt', b'foobar')
    field.process(DummyPostData({'uploads': [file1, file2]}))
    assert len(field.data) == 2
    assert field.data[0]['filename'] == 'baz.txt'
    assert field.data[0]['mimetype'] == 'text/plain'
    assert field.data[0]['size'] == 3
    assert field.data[1]['filename'] == 'foobar.txt'
    assert field.data[1]['mimetype'] == 'text/plain'
    assert field.data[1]['size'] == 6

    assert len(field) == 2
    file_field1, file_field2 = field
    assert file_field1.name == 'uploads-0'
    assert file_field1.action == 'replace'
    assert dictionary_to_binary(file_field1.data) == b'baz'
    assert file_field1.filename == 'baz.txt'
    assert file_field1.file.read() == b'baz'
    assert file_field2.name == 'uploads-1'
    assert file_field2.action == 'replace'
    assert dictionary_to_binary(file_field2.data) == b'foobar'
    assert file_field2.filename == 'foobar.txt'
    assert file_field2.file.read() == b'foobar'

    html = field(force_simple=True)
    assert 'without-data' in html
    assert 'multiple' in html
    assert 'name="uploads"' in html
    assert 'with-data' not in html
    assert 'name="uploads-0"' not in html

    html = field()
    assert 'with-data' in html
    assert 'name="uploads-0"' in html
    assert 'Uploaded file: baz.txt (3 Bytes) ✓' in html
    assert 'name="uploads-1"' in html
    assert 'Uploaded file: foobar.txt (6 Bytes) ✓' in html
    assert 'name="uploads-2"' not in html
    assert 'keep' in html
    assert 'type="file"' in html
    assert 'value="baz.txt"' not in html
    assert 'value="foobar.txt"' not in html
    assert 'Upload additional files' in html
    assert 'name="uploads"' in html
    assert 'without-data' in html
    assert 'multiple' in html

    html = field(resend_upload=True)
    assert 'with-data' in html
    assert 'Uploaded file: baz.txt (3 Bytes) ✓' in html
    assert 'Uploaded file: foobar.txt (6 Bytes) ✓' in html
    assert 'keep' in html
    assert 'type="file"' in html
    assert 'value="baz.txt"' in html
    assert 'value="foobar.txt"' in html

    # Test submit
    form, field = create_field()
    field.process(DummyPostData({}))
    assert field.validate(form)
    assert field.data == []

    form, field = create_field()
    field.process(DummyPostData({'uploads': 'abcd'}))
    assert field.validate(form)  # fails silently
    assert field.data == []

    # ... simple
    form, field = create_field()
    field.process(DummyPostData({'uploads': file2}))
    assert field.validate(form)
    assert len(field) == 1
    assert field[0].action == 'replace'
    assert field.data[0]['filename'] == 'foobar.txt'
    assert field.data[0]['mimetype'] == 'text/plain'
    assert field.data[0]['size'] == 6
    assert dictionary_to_binary(field.data[0]) == b'foobar'
    assert field[0].filename == 'foobar.txt'
    assert field[0].file.read() == b'foobar'

    # ... keep first file and upload a second
    previous = deepcopy(field.data)
    form, field = create_field()
    field.process(DummyPostData({
        'uploads': file1,
        'uploads-0': ['keep', file2]
    }), data=previous)
    assert field.validate(form)
    assert len(field) == 2
    assert field[0].action == 'keep'
    assert field[1].action == 'replace'
    assert field.data[1]['filename'] == 'baz.txt'
    assert field.data[1]['mimetype'] == 'text/plain'
    assert field.data[1]['size'] == 3
    assert dictionary_to_binary(field.data[1]) == b'baz'
    assert field[1].filename == 'baz.txt'
    assert field[1].file.read() == b'baz'

    # ... delete the first file and keep the second
    previous = deepcopy(field.data)
    form, field = create_field()
    field.process(DummyPostData({
        'uploads': '',
        'uploads-0': ['delete', file2],
        'uploads-1': ['keep', file1],
    }), data=previous)
    assert field.validate(form)
    assert len(field) == 2
    assert field[0].action == 'delete'
    assert field.data[0] == {}
    assert field[1].action == 'keep'

    # ... keep second file with keep upload instead of assuming
    # it will be passed backed in via data
    previous = deepcopy(field.data)
    form, field = create_field()
    field.process(DummyPostData({
        'uploads': '',
        # if we omit the first file from the post data the corresponding
        # field will disappear and become the new 0 index
        'uploads-1': [
            'keep', file1, previous[1]['filename'], previous[1]['data']
        ],
    }))
    assert field.validate(form)
    assert len(field) == 1
    assert field[0].action == 'keep'
    assert field[0].data['filename'] == 'baz.txt'
    assert field[0].data['mimetype'] == 'text/plain'
    assert field[0].data['size'] == 3
    assert dictionary_to_binary(field.data[0]) == b'baz'
