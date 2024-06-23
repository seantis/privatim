from privatim.models.file import GeneralFile
from privatim.orm.associable import associated


class AssociatedFiles:
    """ Use this  mixin if uploaded files belong to a specific instance """

    # one-to-many
    files = associated(GeneralFile, 'files')
