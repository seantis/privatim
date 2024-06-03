from uuid import UUID

from sqlalchemy import select
from privatim.models import Consultation, ConsultationDocument
from privatim.models.consultation import Status, Tag
from tests.shared.utils import create_consultation


def test_consultation_status_relationship(session):
    # Creating a status
    status = Status(name='Active')
    session.add(status)
    session.flush()

    # Creating a consultation linked to the status
    consultation = Consultation(
        title='Datenschutzgesetz',
        description='Review the impacts of the proposed construction.',
        recommendation='Proceed with caution',
        status=status
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
        secondary_tags=tags
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


def test_consultation_document(session):

    documents = [
        ConsultationDocument(
            name='document1.pdf',
            content=b'Content of Document 1',
        ),
    ]
    consultation = create_consultation(documents)
    session.add(consultation)
    session.flush()

    smt = select(ConsultationDocument).where(
        ConsultationDocument.filename == 'document1.pdf'
    )
    assert session.execute(smt).scalar_one().content == (
        b'Content of Document 1'
    )
