from sqlalchemy import select

from privatim.models import User
from privatim.models.commentable import Comment
from tests.shared.utils import create_consultation
from tests.shared.utils import create_meeting


def test_commentable_meetings(session):
    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    user = User(email='a@b.ch')
    comment = Comment(content='Test Comment', user=user)
    meeting.comments.append(comment)

    session.add(meeting)
    session.flush()

    assert meeting.comments[0].content == 'Test Comment'


def test_multiple_comments_on_meeting(session):
    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    user1 = User(email='user1@example.com')
    user2 = User(email='user2@example.com')

    comment1 = Comment(content='Comment 1', user=user1)
    comment2 = Comment(content='Comment 2', user=user2)

    meeting.comments.append(comment1)
    meeting.comments.append(comment2)

    session.add(meeting)
    session.flush()

    assert len(meeting.comments) == 2
    assert meeting.comments[0].content == 'Comment 1'
    assert meeting.comments[1].content == 'Comment 2'


def test_simple_comment_delete(session):

    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    user = User(email='user@example.com')
    session.add(user)
    session.flush()

    comment = Comment(content='Test Comment', user=user)
    meeting.comments.append(comment)
    session.add(comment)
    session.flush()

    assert len(meeting.comments) == 1

    meeting.comments.remove(comment)
    session.flush()

    assert len(meeting.comments) == 0


def test_comment_update(session):
    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    user = User(email='user@example.com')
    comment = Comment(content='Initial Comment', user=user)
    meeting.comments.append(comment)

    session.add(meeting)
    session.flush()

    assert meeting.comments[0].content == 'Initial Comment'

    comment.content = 'Updated Comment'
    session.flush()

    assert meeting.comments[0].content == 'Updated Comment'


def test_comment_user_relationship(session):
    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    user = User(email='user@example.com')
    comment = Comment(content='Test Comment', user=user)
    meeting.comments.append(comment)

    session.add(meeting)
    session.flush()

    assert meeting.comments[0].user == user
    assert user.comments[0] == comment


def test_meeting_without_comments(session):
    meeting = create_meeting()
    session.add(meeting)
    session.flush()

    assert len(meeting.comments) == 0


def test_commentable_consultations(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    user = User(email='a@b.ch')
    comment = Comment(content='Test Comment', user=user)
    consultation.comments.append(comment)

    session.add(consultation)
    session.flush()

    assert consultation.comments[0].content == 'Test Comment'


def test_multiple_comments_on_consultation(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    user1 = User(email='user1@example.com')
    user2 = User(email='user2@example.com')

    comment1 = Comment(content='Comment 1', user=user1)
    comment2 = Comment(content='Comment 2', user=user2)

    consultation.comments.append(comment1)
    consultation.comments.append(comment2)

    session.add(consultation)
    session.flush()

    assert len(consultation.comments) == 2
    assert consultation.comments[0].content == 'Comment 1'
    assert consultation.comments[1].content == 'Comment 2'


def test_comment_deletion_consultation(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    user = User(email='user@example.com')
    comment = Comment(content='Test Comment', user=user)
    consultation.comments.append(comment)
    session.add(comment)
    session.add(consultation)
    session.flush()
    assert len(consultation.comments) == 1

    consultation.comments.remove(comment)

    # We can't delete the comment directly, raises FOREIGN KEY constraint
    # failed
    # session.delete(comment)

    session.add(consultation)
    session.flush()

    assert len(consultation.comments) == 0


def test_comment_update_consultation(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    user = User(email='user@example.com')
    comment = Comment(content='Initial Comment', user=user)
    consultation.comments.append(comment)

    session.add(consultation)
    session.flush()

    assert consultation.comments[0].content == 'Initial Comment'

    comment.content = 'Updated Comment'
    session.flush()

    assert consultation.comments[0].content == 'Updated Comment'


def test_comment_user_relationship_consultation(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    user = User(email='user@example.com')
    comment = Comment(content='Test Comment', user=user)
    consultation.comments.append(comment)

    session.add(consultation)
    session.flush()

    assert consultation.comments[0].user == user
    assert user.comments[0] == comment


def test_consultation_without_comments(session):
    consultation = create_consultation()
    session.add(consultation)
    session.flush()

    assert len(consultation.comments) == 0


def test_parent_child_relationship(session):
    user = User(email='user@example.com')
    parent_comment = Comment(content='Parent Comment', user=user)
    child_comment = Comment(
        content='Child Comment', user=user, parent=parent_comment
    )

    session.add(user)
    session.add(parent_comment)
    session.add(child_comment)
    session.flush()

    assert parent_comment.children == [child_comment]
    assert child_comment.parent == parent_comment


def test_sibling_relationship(session):
    user = User(email='user@example.com')
    parent_comment = Comment(content='Parent Comment', user=user)
    sibling1 = Comment(
        content='Sibling Comment 1', user=user, parent=parent_comment
    )
    sibling2 = Comment(
        content='Sibling Comment 2', user=user, parent=parent_comment
    )

    session.add(user)
    session.add(parent_comment)
    session.add(sibling1)
    session.add(sibling2)
    session.flush()

    assert sibling1 in parent_comment.children
    assert sibling2 in parent_comment.children
    assert sibling1 != sibling2

    assert isinstance(sibling1.siblings, list)
    assert isinstance(sibling2.siblings, list)

    # Check siblings for each comment
    sibling1_siblings = sorted(sibling1.siblings, key=lambda c: c.content)
    sibling2_siblings = sorted(sibling2.siblings, key=lambda c: c.content)

    # Use attribute comparison instead of object identity comparison
    expected_siblings_sibling1 = sorted([sibling2], key=lambda c: c.content)
    expected_siblings_sibling2 = sorted([sibling1], key=lambda c: c.content)

    assert [(str(s.id), s.content) for s in sibling1_siblings] == [
        (str(s.id), s.content) for s in expected_siblings_sibling1
    ]
    assert [(str(s.id), s.content) for s in sibling2_siblings] == [
        (str(s.id), s.content) for s in expected_siblings_sibling2
    ]


def test_multiple_children(session):
    user = User(email='user@example.com')
    parent_comment = Comment(content='Parent Comment', user=user)
    child1 = Comment(
        content='Child Comment 1', user=user, parent=parent_comment
    )
    child2 = Comment(
        content='Child Comment 2', user=user, parent=parent_comment
    )

    session.add(user)
    session.add(parent_comment)
    session.add(child1)
    session.add(child2)
    session.flush()

    assert parent_comment.children == [child1, child2]
    assert child1.parent == parent_comment
    assert child2.parent == parent_comment


def test_comment_deletion_with_children(session):
    user = User(email='user@example.com')
    parent_comment = Comment(content='Parent Comment', user=user)
    child_comment = Comment(
        content='Child Comment', user=user, parent=parent_comment
    )

    session.add(user)
    session.add(parent_comment)
    session.add(child_comment)
    session.flush()

    assert parent_comment.children == [child_comment]

    session.delete(parent_comment)
    session.flush()

    assert (
        session.query(Comment).count() == 0
    )  # Both parent and child should be deleted


def test_comment_deletion_without_children(session):
    user = User(email='user@example.com')
    comment = Comment(content='Test Comment', user=user)

    session.add(user)
    session.add(comment)
    session.flush()

    assert session.query(Comment).count() == 1

    session.delete(comment)
    session.flush()

    assert session.query(Comment).count() == 0


def test_nested_comments(session):
    user = User(email='user@example.com')
    grandparent_comment = Comment(content='Grandparent Comment', user=user)
    parent_comment = Comment(
        content='Parent Comment', user=user, parent=grandparent_comment
    )
    child_comment = Comment(
        content='Child Comment', user=user, parent=parent_comment
    )

    session.add(user)
    session.add(grandparent_comment)
    session.add(parent_comment)
    session.add(child_comment)
    session.flush()

    assert grandparent_comment.children == [parent_comment]
    assert parent_comment.parent == grandparent_comment
    assert parent_comment.children == [child_comment]
    assert child_comment.parent == parent_comment
    assert child_comment in parent_comment.children
    assert parent_comment in grandparent_comment.children


def test_sibling_relationship_with_no_parent(session):
    user = User(email='user@example.com')
    sibling1 = Comment(content='Sibling Comment 1', user=user)
    sibling2 = Comment(content='Sibling Comment 2', user=user)

    session.add(user)
    session.add(sibling1)
    session.add(sibling2)
    session.flush()

    assert sibling1.siblings != [sibling2]
    assert sibling2.siblings != [sibling1]


def test_user_deletion_keep_comments(session):
    user = User(email='user@example.com')
    comment1 = Comment(content='Comment 1', user=user)
    comment2 = Comment(content='Comment 2', user=user)

    session.add_all([user, comment1, comment2])
    session.flush()

    assert session.query(Comment).count() == 2

    session.delete(user)
    session.flush()

    assert session.query(User).count() == 0
    comments_query = session.execute(select(Comment)).scalars().all()

    assert {str(comment.id) for comment in comments_query} == {
        str(comment1.id),
        str(comment2.id),
    }
