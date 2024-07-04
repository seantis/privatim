from privatim.models.comment import Comment
from privatim.orm.associable import associated


class Commentable:
    """ Use this in your model to attach a list[Comment] """

    comments = associated(
        Comment, 'comments', 'one-to-many'
    )
