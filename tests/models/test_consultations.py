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


def test_get_latest_version(session):
    # Create initial consultation
    creator = User(email='creator@example.com', first_name='J', last_name='D')
    session.add(creator)
    session.flush()

    # Create a chain of consultations, each replacing the previous one
    consultation_v1 = Consultation(
        title='First Version',
        creator=creator,
        is_latest_version=0,  # Not latest anymore
    )
    session.add(consultation_v1)
    session.flush()

    consultation_v2 = Consultation(
        title='Second Version',
        creator=creator,
        previous_version=consultation_v1,
        is_latest_version=0,
        # Not latest anymore
    )
    consultation_v1.replaced_by = consultation_v2
    session.add(consultation_v2)
    session.flush()

    consultation_v3 = Consultation(
        title='Third Version',
        creator=creator,
        previous_version=consultation_v2,
        is_latest_version=1,  # Latest version
    )
    consultation_v2.replaced_by = consultation_v3
    session.add(consultation_v3)
    session.flush()

    # Test getting latest version from different starting points
    assert consultation_v1.get_latest_version(session) == consultation_v3
    assert consultation_v2.get_latest_version(session) == consultation_v3
    assert consultation_v3.get_latest_version(session) == consultation_v3

    # Verify the chain is correctly linked
    assert consultation_v1.replaced_by == consultation_v2
    assert consultation_v2.replaced_by == consultation_v3
    assert consultation_v3.replaced_by is None

    # Verify is_latest() method works correctly
    assert not consultation_v1.is_latest()
    assert not consultation_v2.is_latest()
    assert consultation_v3.is_latest()

    # Test retrieving from database
    with session.no_consultation_filter():
        stored_v1 = session.execute(
            select(Consultation).filter_by(title='First Version')
        ).scalar_one()

        # Verify we can get to the latest version from a stored consultation
        assert stored_v1.get_latest_version(session) == consultation_v3

        # Test getting latest version when there's only one version
        single_consultation = Consultation(
            title='Single Version', creator=creator, is_latest_version=1
        )
        session.add(single_consultation)
        session.flush()

        _lastest = single_consultation.get_latest_version(session)
        assert _lastest == single_consultation
