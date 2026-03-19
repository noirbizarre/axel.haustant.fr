from dataclasses import dataclass
from pathlib import Path

import qrcode

from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from qrcode.image.styles.moduledrawers import CircleModuleDrawer


@dataclass
class Favicon:
    format: str
    rel: str | None
    dimensions: tuple[int, int]
    prefix: str


ICON_TYPES = (
    Favicon("ico", None, (64, 64), "favicon"),
    Favicon("png", "icon", (16, 16), "favicon"),
    Favicon("png", "icon", (32, 32), "favicon"),
    Favicon("png", "icon", (64, 64), "favicon"),
    Favicon("png", "icon", (96, 96), "favicon"),
    Favicon("png", "icon", (180, 180), "favicon"),
    Favicon("png", "apple-touch-icon", (57, 57), "apple-touch-icon"),
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (60, 60),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (72, 72),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (76, 76),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (114, 114),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (120, 120),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (144, 144),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (152, 152),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (167, 167),
        "prefix": "apple-touch-icon",
    },
    {
        "image_fmt": "png",
        "rel": "apple-touch-icon",
        "dimensions": (180, 180),
        "prefix": "apple-touch-icon",
    },
    {"image_fmt": "png", "rel": None, "dimensions": (70, 70), "prefix": "mstile"},
    {"image_fmt": "png", "rel": None, "dimensions": (270, 270), "prefix": "mstile"},
    {"image_fmt": "png", "rel": None, "dimensions": (310, 310), "prefix": "mstile"},
    {"image_fmt": "png", "rel": None, "dimensions": (310, 150), "prefix": "mstile"},
    {"image_fmt": "png", "rel": "shortcut icon", "dimensions": (196, 196), "prefix": "favicon"},
)


def generate_qr_code(file: Path):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=4,
        image_factory=StyledPilImage,
        mask_pattern=None,
    )
    qr.add_data("https://axel.haustant.fr")
    qr.make(fit=True)
    img = qr.make_image(
        color_mask=RadialGradiantColorMask(
            back_color=(255, 255, 255),
            edge_color=(0, 0, 0),
            center_color=(10, 99, 161),
        ),
        module_drawer=CircleModuleDrawer(),
        embeded_image_path="images/logo-bg-white.png",
    )
    img.save(file)

generate_qr_code(Path() / "images" / "qrcode.png")
