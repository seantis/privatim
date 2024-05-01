from privatim.models.consultation import Status, Consultation


def test_view_add_working_group(client):

    client.login_admin()
    page = client.get('/activities')
    db = client.db

    # add a consultations:
    status = Status(name='Erstellt')
    consultation = Consultation(
        title='Vernehmlassung zur Interkantonalen Vereinbarung über den Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen  ',
        description='Stellungnahme von privatim, Konferenz der schweizerischen Datenschutzbeauftragten, zum Entwurf einer Interkantonalen Vereinbarung über den Datenaustausch zum Betrieb gemeinsamer Abfrageplattformen, zu welcher die Konferenz der Kantonalen Justiz- und Polizeidirektorinnen und –direktoren (KKJPD) zur Zeit eine Vernehmlassung durchführt.',
        recommendation=' Aus verfassungs- und datenschutzrechtlicher Sicht '
        'ergeben sich einerseits grundsätzliche; Vorbehalte '
        'und andererseits Hinweise zu einzelnen Bestimmungen des Vereinbarungsentwurfs..',
        status=status,
    )
    db.add(consultation)
    db.add(status)
    db.flush()

    page = client.get('/activities')
