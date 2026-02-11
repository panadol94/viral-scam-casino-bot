"""Grid collage generator using Pillow."""

import io
import math
from PIL import Image


def create_grid_collage(
    image_bytes_list: list[bytes],
    cell_size: int = 800,
    border: int = 4,
    bg_color: tuple = (30, 30, 30),
) -> bytes:
    """
    Create a grid collage from multiple images.

    Args:
        image_bytes_list: List of image bytes
        cell_size: Size of each cell in pixels (square)
        border: Border/gap between cells in pixels
        bg_color: Background color (dark grey default)

    Returns:
        JPEG bytes of the grid collage
    """
    if not image_bytes_list:
        raise ValueError("No images provided")

    # Single image — return as-is (just optimize)
    if len(image_bytes_list) == 1:
        img = Image.open(io.BytesIO(image_bytes_list[0]))
        img = img.convert("RGB")
        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    count = len(image_bytes_list)

    # Determine grid layout
    if count == 2:
        cols, rows = 2, 1
    elif count == 3:
        cols, rows = 2, 2  # 2 on top, 1 full-width bottom
    elif count == 4:
        cols, rows = 2, 2
    elif count <= 6:
        cols, rows = 3, 2
    elif count <= 9:
        cols, rows = 3, 3
    else:
        cols = 3
        rows = math.ceil(count / 3)

    # Open & resize images to fit cells
    images: list[Image.Image] = []
    for img_bytes in image_bytes_list:
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("RGB")
        img = _resize_crop_center(img, cell_size, cell_size)
        images.append(img)

    # Special layout for 3 images: 2 top + 1 full-width bottom
    if count == 3:
        canvas_w = cell_size * 2 + border * 3
        canvas_h = cell_size * 2 + border * 3
        canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

        # Top row - 2 images
        canvas.paste(images[0], (border, border))
        canvas.paste(images[1], (border * 2 + cell_size, border))

        # Bottom - 1 image full width
        bottom_img = Image.open(io.BytesIO(image_bytes_list[2])).convert("RGB")
        bottom_img = _resize_crop_center(bottom_img, cell_size * 2 + border, cell_size)
        canvas.paste(bottom_img, (border, border * 2 + cell_size))
    else:
        # Standard grid
        canvas_w = cell_size * cols + border * (cols + 1)
        canvas_h = cell_size * rows + border * (rows + 1)
        canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            x = border + col * (cell_size + border)
            y = border + row * (cell_size + border)
            canvas.paste(img, (x, y))

    # Output
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _resize_crop_center(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and center-crop an image to exact dimensions."""
    # Calculate scale to fill target
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return img
