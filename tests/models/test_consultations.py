from sqlalchemy import select
from privatim.models import Consultation, User


def test_consultation_creator_relationship(session):

    creator = User(email='creator@example.com', first_name='J', last_name='D')
    session.add(creator)
    session.flush()

    consultation = Consultation(
        title='foo',
        description='bar',
        recommendation='barfoo',
        creator=creator
    )
    session.add(consultation)
    session.flush()

    stored_consultation = (
        session.execute(
            select(Consultation).filter_by(title='foo')
        ).scalar_one()
    )
    assert stored_consultation is not None

    assert stored_consultation.creator is not None
    assert stored_consultation.creator.email == 'creator@example.com'
