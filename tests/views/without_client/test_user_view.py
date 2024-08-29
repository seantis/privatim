from webob.multidict import MultiDict
from sqlalchemy import select, exists, func
from privatim.models import User, WorkingGroup
from privatim.testing import DummyRequest
from privatim.views.people import (
    add_user_view,
    edit_user_view,
    delete_user_view,
)


def test_add_user_view(pg_config, mailer):
    pg_config.add_route('password_change', '/password_change')
    pg_config.add_route('people', '/people')
    pg_config.add_route('add_user', '/people/add')

    db = pg_config.dbsession
    group = WorkingGroup(name='Test Group')
    db.add(group)
    db.flush()

    request = DummyRequest(
        post=MultiDict(
            {
                'email': 'newuser@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'groups': group.id
            }
        )
    )
    add_user_view(request)

    new_user = db.execute(
        select(User).filter_by(email='newuser@example.com')
    ).scalar_one()
    assert new_user is not None
    assert new_user.first_name == 'New'
    assert new_user.last_name == 'User'
    assert len(new_user.groups) == 1
    assert new_user.groups[0].name == 'Test Group'


def test_add_user_duplicate_email(pg_config, mailer):
    pg_config.add_route('password_change', '/password_change')
    pg_config.add_route('people', '/people')
    db = pg_config.dbsession

    # First, add a user with a specific email
    first_request = DummyRequest(
        post=MultiDict(
            {
                'email': 'user@example.com',
                'first_name': 'First',
                'last_name': 'User',
            }
        )
    )
    add_user_view(first_request)

    # Verify the first user was added successfully
    first_user = db.execute(
        select(User).filter_by(email='user@example.com')
    ).scalar_one()
    assert first_user is not None
    assert first_user.first_name == 'First'

    # Attempt to add another user with the same email
    second_request = DummyRequest(
        post=MultiDict(
            {
                'email': 'user@example.com',
                'first_name': 'Second',
                'last_name': 'User',
            }
        )
    )

    # The view should return a form with errors
    result = add_user_view(second_request)

    # Check that the form in the result contains the expected error
    assert 'form' in result
    form = result['form']
    assert 'email' in form.errors
    assert 'A User with this email already exists.' in form.errors['email']

    # Verify that only one user with this email exists in the database
    user_count = (db.query(func.count()).
                  select_from(User).filter(User.email == 'user@example.com')
                  .scalar())
    assert user_count == 1

    # Verify that the second user was not added
    second_user = db.execute(
        select(User).filter_by(first_name='Second')
    ).scalar_one_or_none()
    assert second_user is None


def test_edit_user_view(pg_config):

    pg_config.add_route('people', '/people')
    pg_config.add_route('person', '/person/{id}')
    pg_config.add_route('edit_user', '/person/{id}/edit')
    db = pg_config.dbsession
    user = User(email='user@example.com', first_name='John', last_name='Doe')
    group = WorkingGroup(name='New Group')
    db.add_all([user, group])
    db.flush()

    request = DummyRequest(
        post=MultiDict(
            {
                'email': 'updated@example.com',
                'first_name': 'Updated',
                'last_name': 'User',
                'groups': group.id
            }
        )
    )
    edit_user_view(user, request)

    updated_user = db.execute(select(User).filter_by(id=user.id)).scalar_one()
    assert updated_user.email == 'updated@example.com'
    assert updated_user.first_name == 'Updated'
    assert updated_user.last_name == 'User'
    assert len(updated_user.groups) == 1
    assert updated_user.groups[0].name == 'New Group'


def test_delete_user_view(pg_config):
    pg_config.add_route('people', '/people')
    db = pg_config.dbsession
    user = User(
        email='delete@example.com', first_name='Delete', last_name='Me'
    )
    db.add(user)
    db.flush()

    request = DummyRequest()
    delete_user_view(user, request)

    not_exists = db.scalar(
        select(~exists().where(User.email == 'delete@example.com'))
    )
    assert not_exists
