from webob.multidict import MultiDict
from sqlalchemy import select
from privatim.models import User
from privatim.models.comment import Comment
from privatim.testing import DummyRequest
from privatim.views import edit_comment_view
from shared.utils import create_consultation


def test_comments_editable(pg_config):

    pg_config.add_route('comment', '/comment/{id}/')
    pg_config.add_route('edit_comment', '/comments/{id}/edit')
    db = pg_config.dbsession
    cons = create_consultation()
    db.add(cons)
    db.flush()

    user = User(email='a@b.ch')
    comment = Comment(content='Original Comment', user=user)
    cons.comments.append(comment)
    request = DummyRequest(post=MultiDict({'content': 'Updated Comment'}))

    edit_comment_view(comment, request)

    updated_comment = db.execute(
        select(Comment).filter_by(id=comment.id)
    ).scalar_one()

    assert updated_comment.content == 'Updated Comment'
    assert updated_comment.content != 'Original Comment'
