from privatim.models.comment import Comment
from privatim.orm.associable import associated
from sqlalchemy.orm import Mapped


class Commentable:
    """ Use this in your model to attach a list[Comment] """

    comments: 'Mapped[list[Comment]]' = associated(
        Comment, 'comments', 'one-to-many'
    )
