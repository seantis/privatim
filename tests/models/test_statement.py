from privatim.models import User, Statement


def test_statement_drafted_by_user(session):
    drafter = User(email='drafter@example.com')
    session.add(drafter)
    session.flush()

    statement_text = 'This is an official statement regarding policy changes.'
    statement = Statement(text=statement_text, drafted_by=drafter.id)
    session.add(statement)
    session.flush()

    stored_statement = session.query(Statement).filter_by(drafted_by=drafter.id).one()
    assert stored_statement is not None
    assert stored_statement.text == statement_text
    assert stored_statement.drafted_by == str(drafter.id)

    assert drafter.statements[0].text == statement_text

