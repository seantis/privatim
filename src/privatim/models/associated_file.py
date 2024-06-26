from sqlalchemy import select
from sqlalchemy.orm import object_session
from sqlalchemy_utils import observes
from privatim.models.file import GeneralFile
from privatim.orm.associable import associated


from typing import Sequence


class AssociatedFiles:
    """ Use this  mixin if uploaded files belong to a specific instance """

    # one-to-many
    files = associated(GeneralFile, 'files')

    def reindex_files(self, searchable_files: Sequence[GeneralFile]) -> None:
        """ Extract the text from the localized files and save it together with
        the language.

        The language is determined by the locale, e.g. `de_CH` -> `german`.

        """

        file: GeneralFile
        # files: dict[str, list[tuple[GeneralFile, bool]]]

        for file in searchable_files:
            print(file)
            # if attribute.extension == 'pdf':
            #     file = SwissVote.__dict__[name].__get_by_locale__(
            #         self, locale
            #     )
            #     if file:
            #         index = name in self.indexed_files
            #         files[locale].append((file, index))
            #
            # setattr(
            #     self,
            #     f'searchable_text_{locale}',
            #     func.to_tsvector(locales[locale], text)
            # )

    def searchable_files(self) -> Sequence[GeneralFile]:
        # For now we just consider PDF's
        stmt = select(GeneralFile).where(
            GeneralFile.content_type == 'application/pdf'
        )
        return object_session(self).execute(stmt).scalars().all()

    @observes('files')
    def files_observer(self) -> None:
        self.reindex_files(self.searchable_files())
