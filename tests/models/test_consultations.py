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

    creator = User(email='creator@example.com')
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


def test_filtered_session_returns_only_latest_version(session):
    # Create two versions of a consultation
    user = User(email='test@example.com')
    status = Status(name='Active')
    session.add_all([user, status])
    session.flush()

    consultation_v1 = Consultation(
        title='Test Consultation',
        description='Version 1',
        creator=user,
        status=status,
        is_latest_version=0
    )
    session.add(consultation_v1)
    session.flush()

    consultation_v2 = Consultation(
        title='Test Consultation',
        description='Version 2',
        creator=user,
        status=status,
        is_latest_version=1
    )
    session.add(consultation_v2)
    session.flush()

    # Query consultations
    result = session.execute(select(Consultation)).scalars().all()

    # Assert that only the latest version is returned
    assert len(result) == 1
    assert result[0].description == 'Version 2'

    # Query consultations without filter
    with session.no_consultation_filter():
        result = session.execute(select(Consultation)).scalars().all()

    # Assert that all versions are returned
    assert len(result) == 2
    assert {r.description for r in result} == {'Version 1', 'Version 2'}
