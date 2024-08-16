from uuid import UUID
from sqlalchemy import select
from privatim.models import Consultation, User
from privatim.models.consultation import Status, Tag


def test_consultation_status_relationship(session):
    consultation = Consultation(
        title='Datenschutzgesetz',
        description='Review the impacts of the proposed construction.',
        recommendation='Proceed with caution',
        status=Status(name='Active'),
        creator=User(email='f@example.org')
    )
    session.add(consultation)
    session.flush()

    # Retrieve and assert correct relationship mappings
    stored_consultation = (
        session.execute(
            select(Consultation).filter_by(title='Datenschutzgesetz')
        ).scalar_one()
    )
    assert stored_consultation is not None
    assert stored_consultation.status is not None
    assert stored_consultation.status.name == 'Active'


def test_consultation_tag(session):

    status = Status(name='Active')
    session.add(status)
    session.flush()

    tags = [Tag(name=n) for n in ['LU', 'SZ']]
    session.add_all(tags)
    session.flush()

    # Creating a consultation linked to the status
    consultation = Consultation(
        title='Datenschutzgesetz',
        description='Review the impacts of the proposed construction.',
        recommendation='Proceed with caution',
        status=status,
        secondary_tags=tags,
        creator=User(email='admin@example.org')
    )
    session.add(consultation)
    session.flush()

    updated_consultation = (
        session.execute(
            select(Consultation).filter_by(title='Datenschutzgesetz')
        ).scalar_one()
    )
    assert updated_consultation.secondary_tags is not None
    tag = updated_consultation.secondary_tags[0]

    def is_uuid(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        UUID(instance)
        return all(instance[position] == "-" for position in (8, 13, 18, 23))

    assert is_uuid(tag.consultation_id)


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
