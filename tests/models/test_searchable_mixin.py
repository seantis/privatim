import transaction
from sqlalchemy import select
from sqlalchemy.orm import undefer
from privatim.models import Consultation
from privatim.models.searchable import reindex_full_text_search


def test_fulltext_indexing_on_searchable_fields(pg_config):
    session = pg_config.dbsession
    consultation = Consultation(
        title='Datenschutz',
        description='cat',
        recommendation='bat',
    )
    session.add(consultation)
    session.flush()

    reindex_full_text_search(session, transaction.manager)

    updated = session.execute(
        select(Consultation)
        .options(undefer(Consultation.searchable_text_de_CH))
        .filter_by(title='Datenschutz')
    ).scalar_one()
    assert updated.searchable_text_de_CH == "'bat':3 'cat':2 'datenschutz':1"
