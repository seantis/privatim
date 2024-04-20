from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import register


DBSession = scoped_session(sessionmaker(expire_on_commit=False))
register(DBSession)
