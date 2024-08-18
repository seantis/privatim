"""
Modified by: cyrill
    - Supports more than one character in the avatar, which was not
    supported before.


Pyavatar Library
~~~~~~~~~~~~~~~~

Pyavatar is a library, written in Python, to generate simple default
user avatars to use in a web application or elsewhere.

:copyright: (c) 2020 by Matthieu Petiteau.
:license: MIT, see LICENSE for more details.
"""

import os
import random
from base64 import b64encode
from enum import Enum, IntEnum
from io import BytesIO
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont


__all__ = (
    "PyAvatar",
    "PyAvatarError",
    "RenderingSizeError",
    "FontpathError",
    "FontExtensionNotSupportedError",
    "ImageExtensionNotSupportedError",
)


class PyAvatarError(Exception):
    """Base PyAvatar error."""

    def __init__(self, value: str, message: str = "", info: str = "") -> None:
        self.value = value
        self.message = message or self.__doc__
        self.info = info
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.value} -> {self.message} {self.info}".strip()


class RenderingSizeError(PyAvatarError):
    """Error with the chosen rendering size."""


class FontpathError(PyAvatarError):
    """Cannot find a font file at this location."""


class FontExtensionNotSupportedError(PyAvatarError):
    """Font file extension not supported."""


class ImageExtensionNotSupportedError(PyAvatarError):
    """Image extension not supported."""


def csv(str_enum: type[Enum]) -> str:
    assert issubclass(str_enum, str) and issubclass(str_enum, Enum)
    return ", ".join(list(str_enum))


class SupportedImageFmt(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    ICO = "ico"


class SupportedFontExt(str, Enum):
    TTF = ".ttf"
    OTF = ".otf"


class SupportedPixelRange(IntEnum):
    MIN = 50
    MAX = 650


_DEFAULT_IMAGE_SIZE = 120
_DEFAULT_FILEPATH = f"{os.getcwd()}/avatar.png"
_DEFAULT_FONT_FILEPATH = os.path.join(
    os.path.dirname(__file__), "font/Lora.ttf"
)

_HexColor: TypeAlias = str
_RGBColor: TypeAlias = tuple[int, int, int]


class PyAvatar:
    """Generate a default avatar from a given string input.

    :param text: Input text to use in the avatar.
    :param size: (optional) Integer, size in pixel of the avatar.
    :param fontpath: (optional) Filepath to the font file to use.
    :param color: (optional) hex or rgb color code for the background.
    :type color: string or tuple
    :param capitalize: (optional) Boolean, capitalize the first letter.
    :type capitalize: bool

    Usage::
      >>> from pyavatar import PyAvatar
      >>> avatar = PyAvatar("smallwat3r", size=250)
      >>> avatar.color
      (191, 91, 81)
      >>> avatar.change_color()
      >>> avatar.color
      (203, 22, 126)
      >>> avatar.stream("png")
      b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\xfa\x00\x00 ...'
      >>> avatar.base64_image("jpeg")
      'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBg ...'
      >>> import os
      >>> avatar.save(f"{os.getcwd()}/me.png")
    """

    def __init__(
        self,
        text: str,
        size: int = _DEFAULT_IMAGE_SIZE,
        fontpath: str = _DEFAULT_FONT_FILEPATH,
        color: _HexColor | _RGBColor | None = None,
        capitalize: bool = True,
        char_spacing: int = 0,
    ):
        self.text = text
        if capitalize:
            self.text = self.text.upper()
        self.size = size
        self.fontpath = fontpath
        self.color = color or self._random_color()
        self.char_spacing = char_spacing
        self.image = self.__generate_avatar()

    def __str__(self) -> str:
        return f"{self.text} {self.size}x{self.size} {self.color}"

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Attribute `text` must be a string.")
        if len(value) > 3:
            raise ValueError("Text must be 3 characters or less.")
        self._text = value[:3]  # Limit to the first three characters

    @property
    def char_spacing(self) -> int:
        return self._char_spacing

    @char_spacing.setter
    def char_spacing(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("Attribute `char_spacing` must be an integer.")
        if value < 0:
            raise ValueError("Character spacing must be non-negative.")
        self._char_spacing = value

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("Attribute `size` must be an integer.")
        if value < SupportedPixelRange.MIN or value > SupportedPixelRange.MAX:
            raise RenderingSizeError(
                str(value),
                (
                    "Size must fit within range "
                    f"min={SupportedPixelRange.MIN} "
                    f"max={SupportedPixelRange.MAX}."
                ),
            )
        self._size = value

    @property
    def fontpath(self) -> str:
        return self._fontpath

    @fontpath.setter
    def fontpath(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Attribute `fontpath` must be a string.")
        if not os.path.exists(value):
            raise FontpathError(value)
        if not value.lower().endswith(tuple(SupportedFontExt)):
            raise FontExtensionNotSupportedError(
                os.path.basename(value),
                info=f"Supported extensions: {csv(SupportedFontExt)}.",
            )
        self._fontpath = value

    @staticmethod
    def _random_color() -> _RGBColor:
        return (
            random.randint(0, 255),  # nosec
            random.randint(0, 255),  # nosec
            random.randint(0, 255),  # nosec
        )

    def __generate_avatar(self) -> Image.Image:
        image = Image.new(
            mode="RGB", size=(self.size, self.size), color=self.color
        )
        font_size = int(
            0.9 * self.size / len(self.text)
        )  # Slightly reduced to accommodate spacing
        font = ImageFont.truetype(self.fontpath, size=font_size)
        draw = ImageDraw.Draw(image)

        # Calculate total width including spacing
        total_width = sum(
            draw.textlength(char, font) for char in self.text
        ) + self.char_spacing * (len(self.text) - 1)
        total_height = max(
            font.getbbox(char)[3] - font.getbbox(char)[1] for char in self.text
        )

        # Calculate starting position
        start_x = (self.size - total_width) / 2
        start_y = (self.size - total_height) / 2 - self.size * 0.1

        # Draw each character with spacing
        for char in self.text:
            char_width = draw.textlength(char, font)
            draw.text((start_x, start_y), char, font=font, fill='white')
            start_x += char_width + self.char_spacing

        return image

    def change_color(self, color: _HexColor | _RGBColor | None = None) -> None:
        """Redraw the avatar with a new background color.

        :param color: (optional) hex or rgb color code for the background.
        :type color: string or tuple
        """
        self.color = color or self._random_color()
        self.image = self.__generate_avatar()

    def save(self, filepath: str = _DEFAULT_FILEPATH) -> None:
        """Save the avatar under a given file path.

        :param filepath: (optional) Filepath where the avatar will be saved.
        """
        extension = os.path.splitext(filepath)[1].split(".")[1]
        if extension not in set(SupportedImageFmt):
            raise ImageExtensionNotSupportedError(
                os.path.basename(filepath),
                info=f"Supported formats: {csv(SupportedImageFmt)}.",
            )
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.image.save(filepath, optimize=True)

    def stream(
        self, filetype: SupportedImageFmt = SupportedImageFmt.PNG
    ) -> bytes:
        """Save the avatar in a bytes array.

        :param filetype: (optional) Avatar file format.
        :rtype: bytes
        """
        if filetype.lower() not in set(SupportedImageFmt):
            raise ImageExtensionNotSupportedError(
                filetype, info=f"Supported formats: {csv(SupportedImageFmt)}."
            )
        stream = BytesIO()
        self.image.save(stream, format=filetype.value, optimize=True)
        return stream.getvalue()

    def base64_image(
        self, filetype: SupportedImageFmt = SupportedImageFmt.PNG
    ) -> str:
        """Save the avatar as a base64 image.

        :param filetype: (optional) Avatar file format.
        :rtype: str
        """
        encoded_image = b64encode(self.stream(filetype)).decode("utf-8")
        return f"data:image/{filetype.value};base64,{encoded_image}"
