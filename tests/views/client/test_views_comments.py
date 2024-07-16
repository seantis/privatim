from pathlib import Path
from webtest import Upload
from privatim.models import User
from privatim.static import get_default_profile_pic_data
from tests.shared.utils import create_consultation


def test_add_comment(client):
    consultation = create_consultation()
    session = client.db

    client.login_admin()
    session.add(consultation)
    session.commit()
    session.refresh(consultation)
    page = client.get(f'/consultation/{consultation.id}')
    assert page.status_code == 200

    page.form['content'] = 'What an interesting thought'
    page = page.form.submit().follow()
    assert page.status_code == 200
    assert 'What an interesting thought' in page


def test_profile_picture_author_is_rendered_in_comment(client):
    consultation = create_consultation()
    session = client.db

    client.login_admin()
    session.add(consultation)
    session.commit()
    session.refresh(consultation)
    page = client.get(f'/consultation/{consultation.id}')
    assert page.status_code == 200

    page.form['content'] = 'Comment is here'
    page = page.form.submit().follow()
    assert page.status_code == 200

    user2 = User(email='user1@example.com')
    session.add(user2)
    session.flush()
    user2.set_password('test')
    session.add(user2)
    session.commit()

    # add another comment
    client.login(user2.email, 'test')
    page = client.get('/profile')
    file = Path(__file__).parent / 'pic' / 'pict.png'
    bytes_profile_pic = file.read_bytes()
    page.form['profilePic'] = Upload('pict.png', bytes_profile_pic)
    page = page.form.submit().follow()
    assert page.status_code == 200

    page = client.get(f'/consultation/{consultation.id}')
    page.forms[2]['content'] = 'Another Comment is here'
    page = page.forms[2].submit().follow()

    assert page.status_code == 200
    # now check the comment to have the profile pic

    page = client.get(f'/consultation/{consultation.id}')
    imgs = page.pyquery('img.comment-picture')
    assert len(imgs) == 2
    files = [client.get(link).body for link in (e.get('src') for e in imgs)]
    # first comment has the default picture
    first_comment_picture = files[0]
    assert first_comment_picture == get_default_profile_pic_data()[1]

    # second comment should have the custom picture
    second_comment_picture = files[1]
    assert second_comment_picture == bytes_profile_pic
