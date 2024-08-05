from sqlalchemy import select
from privatim.models import User
from privatim.models.consultation import Status, Consultation


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
