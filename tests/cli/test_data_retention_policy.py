from datetime import timedelta
from sedate import utcnow
from sqlalchemy import select

from privatim.cli.apply_data_retention_policy import (
    delete_old_consultation_chains,
)
from privatim.models import Consultation, SearchableFile


def create_consultation(
    session, user, title, days_old, is_deleted=False, with_file=False
):
    """Helper function to create a consultation"""

    consultation = Consultation(
        title=title,
        creator=user,
        description='Test description',
        status='Created',
    )

    if with_file:
        file = SearchableFile(
            filename='test.txt',
            content=b'Test content',
        )
        session.add(file)
        consultation.files.append(file)

    # updated will be accesssed
    consultation.created = utcnow() - timedelta(days=days_old)
    consultation.deleted = is_deleted
    session.add(consultation)
    session.flush()
    return consultation


def test_delete_old_records_consultations(session, user):
    # Create various consultations
    create_consultation(session, user, 'Recent Active', 10)
    create_consultation(session, user, 'Old Active', 40)
    old_deleted = create_consultation(
        session, user, 'Old Deleted', 40, is_deleted=True
    )
    old_deleted_with_file = create_consultation(
        session,
        user,
        'Old Deleted with File',
        40,
        is_deleted=True,
        with_file=True,
    )
    create_consultation(session, user, 'Recent Deleted', 10, is_deleted=True)

    session.flush()

    # Run the delete_old_consultation_chains function
    deleted_ids = delete_old_consultation_chains(session, days_threshold=30)

    # Check that the correct consultations were deleted
    assert len(deleted_ids) == 2
    assert old_deleted.id in deleted_ids
    assert old_deleted_with_file.id in deleted_ids

    with session.no_soft_delete_filter():
        remaining_consultations = session.scalars(select(Consultation)).all()
        remaining_ids = [c.id for c in remaining_consultations]

        assert len(remaining_consultations) == 3
        assert old_deleted.id not in remaining_ids
        assert old_deleted_with_file.id not in remaining_ids

        # Check that associated files were also deleted
        remaining_files = session.scalars(select(SearchableFile)).all()
        assert len(remaining_files) == 0


def test_delete_old_consultation_chains_no_deletions(session, user):
    # Create only recent or active consultations
    create_consultation(session, user, 'Recent Active', 10)
    create_consultation(session, user, 'Recent Deleted', 10, is_deleted=True)

    session.flush()

    # Run the delete_old_consultation_chains function
    deleted_ids = delete_old_consultation_chains(session)

    # Check that no consultations were deleted
    assert len(deleted_ids) == 0

    with session.no_soft_delete_filter():
        remaining_consultations = session.scalars(select(Consultation)).all()
        assert len(remaining_consultations) == 2
