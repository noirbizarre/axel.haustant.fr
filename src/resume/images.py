import shutil

from dataclasses import dataclass
from pathlib import Path

import qrcode

from PIL import Image

from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from qrcode.image.styles.moduledrawers import CircleModuleDrawer


@dataclass
class Favicon:
    format: str
    rel: str | None
    dimensions: tuple[int, int]
    prefix: str

    @property
    def filename(self) -> str:
        w, h = self.dimensions
        return f"{self.prefix}-{w}x{h}.{self.format}"

    @property
    def mime_type(self) -> str:
        if self.format == "ico":
            return "image/x-icon"
        return f"image/{self.format}"

    @property
    def sizes(self) -> str:
        return f"{self.dimensions[0]}x{self.dimensions[1]}"


ICON_TYPES = (
    Favicon("ico", None, (64, 64), "favicon"),
    Favicon("png", "icon", (16, 16), "favicon"),
    Favicon("png", "icon", (32, 32), "favicon"),
    Favicon("png", "icon", (64, 64), "favicon"),
    Favicon("png", "icon", (96, 96), "favicon"),
    Favicon("png", "icon", (180, 180), "favicon"),
    Favicon("png", "apple-touch-icon", (57, 57), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (60, 60), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (72, 72), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (76, 76), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (114, 114), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (120, 120), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (144, 144), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (152, 152), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (167, 167), "apple-touch-icon"),
    Favicon("png", "apple-touch-icon", (180, 180), "apple-touch-icon"),
    Favicon("png", None, (70, 70), "mstile"),
    Favicon("png", None, (270, 270), "mstile"),
    Favicon("png", None, (310, 310), "mstile"),
    Favicon("png", None, (310, 150), "mstile"),
    Favicon("png", "shortcut icon", (196, 196), "favicon"),
)


def generate_favicons(source: Path, out_dir: Path, *, root_dir: Path | None = None):
    """Generate all favicon variants from *source* image into *out_dir*.

    Args:
        source: Path to the source logo image (e.g. ``logo.png``).
        out_dir: Directory where favicon files will be written.
        root_dir: If provided, also copy ``favicon.ico`` here for legacy compatibility.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(source).convert("RGBA")

    for fav in ICON_TYPES:
        resized = img.resize(fav.dimensions, Image.Resampling.LANCZOS)
        out_file = out_dir / fav.filename
        if fav.format == "ico":
            resized.save(out_file, format="ICO")
        else:
            resized.save(out_file, format="PNG")

    if root_dir is not None:
        ico_favicon = next(f for f in ICON_TYPES if f.format == "ico")
        shutil.copy2(out_dir / ico_favicon.filename, root_dir / "favicon.ico")


def generate_qr_code(file: Path, url: str, *, logo: Path | None = None):
    """Generate a styled QR code linking to *url* and save it to *file*.

    Args:
        file: Destination path for the generated PNG image.
        url: The URL to encode in the QR code.
        logo: Optional logo image to embed in the centre of the QR code.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=4,
        image_factory=StyledPilImage,
        mask_pattern=None,
    )
    qr.add_data(url)
    qr.make(fit=True)
    kwargs: dict = {
        "color_mask": RadialGradiantColorMask(
            back_color=(255, 255, 255, 0),
            edge_color=(0, 0, 0, 255),
            center_color=(10, 99, 161, 255),
        ),
        "module_drawer": CircleModuleDrawer(),
    }
    if logo and logo.exists():
        kwargs["embeded_image_path"] = str(logo)
    img = qr.make_image(**kwargs)
    file.parent.mkdir(parents=True, exist_ok=True)
    img.save(file)
