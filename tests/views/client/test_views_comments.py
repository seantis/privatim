from tests.shared.utils import create_consultation


def test_add_comment(client):
    consultation = create_consultation()
    session = client.db

    client.login_admin()
    session.add(consultation)
    session.flush()
    session.refresh(consultation)
    page = client.get(f'/consultation/{consultation.id}')
    assert page.status_code == 200

    page.form['content'] = 'What an interesting thought'
    page = page.form.submit().follow()
    assert page.status_code == 200
    assert 'What an interesting thought' in page
