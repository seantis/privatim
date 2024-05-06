from sqlalchemy import select
from privatim.models import Consultation
from privatim.models.consultation import Status


def test_consultation_status_relationship(session):
    # Creating a status
    status = Status(name='Active')
    session.add(status)
    session.flush()

    # Creating a consultation linked to the status
    consultation = Consultation(
        title='Datenschutzgesetz',
        description='Review the impacts of the proposed construction.',
        comments='Needs further details on wildlife impacts.',
        recommendation='Proceed with caution',
        status_id=status.id
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

    # Assert status lintage
    assert stored_consultation.status is not None
    assert stored_consultation.status.name == 'Active'

    stored_consultation.comments = 'Updated comments after review.'
    session.flush()

    updated_consultation = (
        session.execute(
            select(Consultation).filter_by(title='Datenschutzgesetz')
        ).scalar_one()
    )
    assert updated_consultation.comments == 'Updated comments after review.'
