"""
Generate a Swiss flag icon (.icns) for the SwissTaxAgent macOS app.
Usage: python3 scripts/make_icon.py <output.icns>
"""

import os
import sys
import shutil
import subprocess
import tempfile

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow not found. Installing…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw


SWISS_RED = (213, 43, 30)
WHITE = (255, 255, 255)

ICON_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def draw_swiss_flag(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), SWISS_RED)
    draw = ImageDraw.Draw(img)

    # Swiss cross proportions (federal spec):
    # Cross arm width = 6/20 of flag, arm length = 12/20 of flag, centred
    arm_w = round(size * 6 / 20)
    arm_h = round(size * 12 / 20)
    cx = size // 2
    cy = size // 2

    # Horizontal bar
    draw.rectangle(
        [cx - arm_h // 2, cy - arm_w // 2, cx + arm_h // 2, cy + arm_w // 2],
        fill=WHITE,
    )
    # Vertical bar
    draw.rectangle(
        [cx - arm_w // 2, cy - arm_h // 2, cx + arm_w // 2, cy + arm_h // 2],
        fill=WHITE,
    )
    return img


def build_icns(output_path: str) -> None:
    iconset_dir = tempfile.mkdtemp(suffix=".iconset")
    try:
        for size in ICON_SIZES:
            img = draw_swiss_flag(size)
            img.save(os.path.join(iconset_dir, f"icon_{size}x{size}.png"))
            # Retina versions
            if size <= 512:
                retina = draw_swiss_flag(size * 2)
                retina.save(os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png"))

        subprocess.check_call(["iconutil", "-c", "icns", iconset_dir, "-o", output_path])
        print(f"Icon created: {output_path}")
    finally:
        shutil.rmtree(iconset_dir)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "AppIcon.icns"
    build_icns(out)
