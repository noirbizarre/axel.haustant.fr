import shutil

from dataclasses import dataclass
from pathlib import Path

import qrcode

from PIL import Image, ImageDraw, ImageFont

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


SOCIAL_PREVIEW_FILENAME = "social-preview.png"
SOCIAL_PREVIEW_WIDTH = 1200
SOCIAL_PREVIEW_HEIGHT = 630

# Brand colours matching style/web.css
_PRIMARY = (91, 137, 180)  # #5b89b4
_PRIMARY_DARK = (61, 104, 145)  # #3d6891
_PRIMARY_LIGHT = (123, 163, 200)  # #7ba3c8

# Font search order — try PT Sans first, fall back to common sans-serif fonts.
_FONT_CANDIDATES = [
    "PT Sans",
    "Liberation Sans",
    "DejaVu Sans",
    "Noto Sans",
    "Arial",
]

_FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/noto/NotoSans-Bold.ttf",
]

_FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
]


def _find_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try loading the first available font from *candidates*."""
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default(size)


def _make_circular_avatar(img: Image.Image, size: int) -> Image.Image:
    """Resize *img* and apply a circular mask."""
    img = img.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def generate_social_preview(
    out_dir: Path,
    *,
    full_name: str,
    tagline: str = "",
    avatar_path: Path | None = None,
    url: str = "",
) -> Path:
    """Generate a social preview card (1200x630 PNG) using Pillow.

    Args:
        out_dir: Directory where the image will be written.
        full_name: The person's full name (displayed prominently).
        tagline: Job title or tagline (displayed below the name).
        avatar_path: Path to the avatar image file.
        url: Site URL to display at the bottom of the card.

    Returns:
        Path to the generated PNG file.
    """
    W, H = SOCIAL_PREVIEW_WIDTH, SOCIAL_PREVIEW_HEIGHT
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / SOCIAL_PREVIEW_FILENAME

    # -- Create gradient background ------------------------------------------
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    for x in range(W):
        # Horizontal gradient: primary-dark → primary → primary-light
        t = x / W
        r = int(_PRIMARY_DARK[0] + (_PRIMARY_LIGHT[0] - _PRIMARY_DARK[0]) * t)
        g = int(_PRIMARY_DARK[1] + (_PRIMARY_LIGHT[1] - _PRIMARY_DARK[1]) * t)
        b = int(_PRIMARY_DARK[2] + (_PRIMARY_LIGHT[2] - _PRIMARY_DARK[2]) * t)
        draw.line([(x, 0), (x, H)], fill=(r, g, b))

    # -- Subtle decorative circles -------------------------------------------
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Top-right circle
    overlay_draw.ellipse(
        (W - 240, -80, W + 80, 240),
        outline=(255, 255, 255, 20),
        width=3,
    )
    # Bottom-left circle
    overlay_draw.ellipse(
        (-60, H - 240, 180, H + 60),
        outline=(255, 255, 255, 15),
        width=3,
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    # -- Load fonts -----------------------------------------------------------
    font_name = _find_font(_FONT_BOLD_CANDIDATES, 52)
    font_tagline = _find_font(_FONT_REGULAR_CANDIDATES, 26)
    font_url = _find_font(_FONT_REGULAR_CANDIDATES, 18)

    # -- Layout: compute vertical positions -----------------------------------
    avatar_size = 140
    border_width = 4
    spacing = 24  # gap between elements
    name_upper = full_name.upper()

    # Measure text dimensions
    name_bbox = draw.textbbox((0, 0), name_upper, font=font_name)
    name_h = name_bbox[3] - name_bbox[1]

    tagline_h = 0
    if tagline:
        tagline_bbox = draw.textbbox((0, 0), tagline, font=font_tagline)
        tagline_h = tagline_bbox[3] - tagline_bbox[1]

    url_h = 0
    if url:
        url_bbox = draw.textbbox((0, 0), url, font=font_url)
        url_h = url_bbox[3] - url_bbox[1]

    # Total content height
    total_h = avatar_size + spacing + name_h
    if tagline:
        total_h += spacing + tagline_h
    total_h += spacing + 3  # separator line
    if url:
        total_h += spacing + url_h

    y = (H - total_h) // 2

    # -- Draw avatar ----------------------------------------------------------
    if avatar_path and avatar_path.exists():
        avatar_img = _make_circular_avatar(Image.open(avatar_path), avatar_size)
        # White border ring
        ring_size = avatar_size + border_width * 2
        border_ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
        ring_draw = ImageDraw.Draw(border_ring)
        ring_draw.ellipse(
            (0, 0, ring_size, ring_size),
            fill=(255, 255, 255, 230),
        )
        ring_x = (W - ring_size) // 2
        img.paste(border_ring, (ring_x, int(y - border_width)), border_ring)
        avatar_x = (W - avatar_size) // 2
        img.paste(avatar_img, (avatar_x, int(y)), avatar_img)

    y += avatar_size + spacing

    # -- Draw name ------------------------------------------------------------
    draw.text(
        (W // 2, y),
        name_upper,
        fill=(255, 255, 255),
        font=font_name,
        anchor="mt",
    )
    y += name_h + spacing

    # -- Draw tagline ---------------------------------------------------------
    if tagline:
        draw.text(
            (W // 2, y),
            tagline,
            fill=(255, 255, 255, 230),
            font=font_tagline,
            anchor="mt",
        )
        y += tagline_h + spacing

    # -- Draw separator -------------------------------------------------------
    sep_w = 80
    draw.line(
        [(W // 2 - sep_w // 2, y + 1), (W // 2 + sep_w // 2, y + 1)],
        fill=(255, 255, 255, 128),
        width=3,
    )
    y += 3 + spacing

    # -- Draw URL -------------------------------------------------------------
    if url:
        display_url = url.replace("https://", "").replace("http://", "").strip("/")
        draw.text(
            (W // 2, y),
            display_url,
            fill=(255, 255, 255, 180),
            font=font_url,
            anchor="mt",
        )

    # -- Save -----------------------------------------------------------------
    img.convert("RGB").save(out_file, format="PNG")
    return out_file
