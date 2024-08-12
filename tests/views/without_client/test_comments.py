from webob.multidict import MultiDict
from sqlalchemy import select, exists
from privatim.models import User
from privatim.models import Comment, Consultation
from privatim.testing import DummyRequest
from privatim.views.comment import edit_comment_view, delete_comment_view
from shared.utils import create_consultation


def test_comment_editable(pg_config):

    pg_config.add_route('comment', '/comment/{id}/')
    pg_config.add_route('edit_comment', '/comments/{id}/edit')
    db = pg_config.dbsession
    cons = create_consultation()
    db.add(cons)
    comment = Comment(
        content='Original Comment',
        user=User(email='a@b.ch'),
        target_id=cons.id
    )
    db.add(comment)
    db.flush()
    request = DummyRequest(post=MultiDict({'content': 'Updated Comment'}))

    edit_comment_view(comment, request)

    updated_comment = db.execute(
        select(Comment).filter_by(id=comment.id)
    ).scalar_one()

    assert updated_comment.content == 'Updated Comment'
    assert updated_comment.content != 'Original Comment'


def test_comment_delete(pg_config):
    pg_config.add_route('consultation', '/consultation/{id}/')
    pg_config.add_route('comment', '/comment/{id}/')
    pg_config.add_route('delete_comment', '/comments/{id}/delete')
    db = pg_config.dbsession
    cons = create_consultation()

    comment = Comment('El Commento', User(email='a@b.ch'), target_id=cons.id)
    cons.comments.append(comment)
    db.add(cons)
    db.add(comment)
    db.flush()
    db.refresh(comment)

    request = DummyRequest()
    delete_comment_view(comment, request)

    not_exists = db.scalar(
        select(~exists().where(Comment.content == 'El Commento'))
    )
    assert not_exists
    return

    cons = db.scalar(select(Consultation).filter(Consultation.id == cons.id))
    assert cons.comments == []
