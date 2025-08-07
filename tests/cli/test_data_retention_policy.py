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
    # Add and flush consultation first to get an ID for the file FK
    session.add(consultation)
    session.flush()

    if with_file:
        file = SearchableFile(
            filename='test.txt',
            content=b'Test content',
            consultation_id=consultation.id  # Set parent ID directly
        )
        # No need for consultation.files.append(file), FK relationship handles
        session.add(file)

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


def test_delete_old_consultation_chains_handles_files_correctly(session, user):
    # Setup:
    # 1. Consultation to be deleted (old, soft-deleted) WITH a file
    consultation_to_delete_with_file = create_consultation(
        session,
        user,
        'Old Deleted With File To Go',
        40,
        is_deleted=True,
        with_file=True
    )
    file_to_be_deleted_id = consultation_to_delete_with_file.files[0].id

    # 2. Consultation to be deleted (old, soft-deleted) WITHOUT a file
    consultation_to_delete_no_file = create_consultation(
        session, user, 'Old Deleted No File To Go', 40, is_deleted=True
    )

    # 3. Consultation NOT to be deleted (recent, soft-deleted) WITH a file
    consultation_recent_with_file = create_consultation(
        session,
        user,
        'Recent Deleted With File To Keep',
        10,
        is_deleted=True,
        with_file=True
    )
    file_to_be_kept_recent_id = consultation_recent_with_file.files[0].id

    # 4. Consultation NOT to be deleted (old, NOT soft-deleted) WITH a file
    consultation_active_with_file = create_consultation(
        session,
        user,
        'Old Active With File To Keep',
        40,
        is_deleted=False,
        with_file=True
    )
    file_to_be_kept_active_id = consultation_active_with_file.files[0].id

    session.flush()

    # Run the delete_old_consultation_chains function
    deleted_consultation_ids = delete_old_consultation_chains(
        session, days_threshold=30
    )

    # Assertions:
    assert len(deleted_consultation_ids) == 2
    assert consultation_to_delete_with_file.id in deleted_consultation_ids
    assert consultation_to_delete_no_file.id in deleted_consultation_ids

    with session.no_soft_delete_filter():
        # Check consultations
        remaining_consultations_count = session.query(Consultation).count()
        assert remaining_consultations_count == 2
        assert session.get(Consultation, consultation_recent_with_file.id)
        assert session.get(Consultation, consultation_active_with_file.id)

        # Check files
        remaining_files_count = session.query(SearchableFile).count()
        assert remaining_files_count == 2
        assert session.get(SearchableFile, file_to_be_deleted_id) is None
        assert session.get(SearchableFile, file_to_be_kept_recent_id)
        assert session.get(SearchableFile, file_to_be_kept_active_id)
