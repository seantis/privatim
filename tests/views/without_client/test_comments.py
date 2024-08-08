from privatim.models import User
from privatim.models.comment import Comment
from privatim.views import edit_comment_view
from shared.utils import create_consultation


def test_sortable_agenda_items_view(pg_config):
    pg_config.add_route('edit_comment', '/comments/{id}/edit')
    db = pg_config.dbsession
    cons = create_consultation()
    db.add(cons)
    db.flush()

    user = User(email='a@b.ch')
    comment = Comment(content='Test Comment', user=user)
    cons.comments.append(comment)

    agenda_items = [
        {'title': 'Introduction', 'description': 'Welcome and introductions.'},
        {'title': 'Project Update', 'description': 'Update on projects.'},
    ]

    meeting = edit_comment_view(comment, db)

    assert [[e.title, e.position] for e in meeting.agenda_items] == [
        ['Introduction', 0],
        ['Project Update', 1]
    ]
