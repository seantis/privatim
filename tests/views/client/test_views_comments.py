from tests.shared.utils import create_consultation


def test_add_comment(client):
    consultation = create_consultation()
    session = client.db

    client.login_admin()
    session.add(consultation)
    session.flush()
    session.refresh(consultation)

    page = client.get(f'/consultations/{consultation.id}')
    assert page.status_code == 200

    # form = page.forms.get('add_comment_form')

    page.form['content'] = 'What an interesting thought'
    # ? this is 404, but works if manually tested... weird

    page = page.form.submit().follow()
    assert page.status_code == 200
    assert 'What an interesting thought' in page
