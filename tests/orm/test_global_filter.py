from sqlalchemy import select
from privatim.models import User, SearchableFile
from privatim.models.consultation import Status, Consultation
from tests.shared.utils import create_consultation


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


def test_filtered_session_soft_delete_consultation(session):

    # Create a consultation
    file = SearchableFile(
        filename='document1.txt',
        content=b'Content of Document 1',
    )
    consultation = create_consultation(documents=[file])
    session.add(consultation)
    session.flush()

    # Verify consultation is returned in normal query
    result = session.execute(select(Consultation)).scalars().all()
    assert len(result) == 1
    assert result[0].title == 'Test Consultation'

    # Soft delete the consultation
    session.delete(consultation, soft=True)
    session.flush()

    # Verify consultation is not returned in normal query
    result = session.execute(select(Consultation)).scalars().all()
    assert len(result) == 0

    # same for file: The file will be soft deleted via cascade
    files = session.execute(select(SearchableFile).where(
        SearchableFile.filename == 'document1.txt'
    )).scalars().all()
    assert len(files) == 0

    # Verify consultation and file is returned when filter is disabled
    with session.no_soft_delete_filter():
        result = session.execute(select(Consultation)).scalars().all()
        assert len(result) == 1
        assert result[0].title == 'Test Consultation'
        assert result[0].deleted is True

        files = session.execute(select(SearchableFile).where(
            SearchableFile.filename == 'document1.txt'
        )).scalars().all()
        assert len(files) == 1
