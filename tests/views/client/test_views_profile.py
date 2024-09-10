from pathlib import Path
from sqlalchemy import select
from webtest.forms import Upload
from privatim.models import GeneralFile


def test_profile_image_upload(client):
    client.login_admin()
    page = client.get('/profile')

    page.form['profilePic'] = Upload('empty.png', b'')
    page = page.form.submit().follow()
    assert 'Hochgeladene Datei ist leer' in page

    # Test case 3: Invalid file type
    page.form['profilePic'] = Upload('invalid.txt', b'Invalid content')
    page = page.form.submit().follow()
    assert 'Ungültiger Dateityp' in page

    # Test case 4: File too large (create a file > 5MB)
    large_content = b'0' * (5 * 1024 * 1024 + 1)
    page.form['profilePic'] = Upload('large.png', large_content)
    page = page.form.submit().follow()
    assert 'Dateigrösse überschreitet 5MB-Limit' in page

    # Test case 5: Invalid image content
    page.form['profilePic'] = Upload('fake.png', b'Not a real PNG')
    page = page.form.submit().follow()
    assert 'Ungültige Bilddatei' in page

    # Test case 6: Valid image file
    file = Path(__file__).parent / 'pic' / 'pict.png'
    bytes_profile_pic = file.read_bytes()
    page.form['profilePic'] = Upload('pict.png', bytes_profile_pic)
    page = page.form.submit().follow()
    assert 'erfolgreich geändert' in page
    assert page.status_code == 200

    # Check the image in the database
    stmt = select(GeneralFile).where(GeneralFile.filename == 'pict.png')
    general_file = client.db.execute(stmt).scalar_one_or_none()
    assert general_file is not None
    assert general_file.content == bytes_profile_pic
