"""
Generate simple PNG icons for the EALE Chrome Extension.
No external dependencies — uses only Python stdlib (struct + zlib).

Run from the chrome-extension/ directory:
    python3 generate_icons.py
"""
import os
import struct
import zlib


def make_png(size: int, bg_rgb=(79, 70, 229), fg_rgb=(255, 255, 255)) -> bytes:
    """
    Create a minimal solid-colour PNG of `size` × `size` px.
    Draws a simple 'E' character by setting pixels directly.
    """
    r_bg, g_bg, b_bg = bg_rgb
    r_fg, g_fg, b_fg = fg_rgb

    # Build raw pixel data (RGB, no alpha)
    pixels = [bg_rgb] * (size * size)

    # Draw a crude 'E' shape centred in the icon
    # We work in a virtual 7×9 grid and scale up
    glyph = [
        "XXXXX",
        "X    ",
        "X    ",
        "XXXX ",
        "X    ",
        "X    ",
        "XXXXX",
    ]
    gw, gh = len(glyph[0]), len(glyph)
    scale_x = max(1, size // (gw + 2))
    scale_y = max(1, size // (gh + 2))
    off_x = (size - gw * scale_x) // 2
    off_y = (size - gh * scale_y) // 2

    for gy, row in enumerate(glyph):
        for gx, ch in enumerate(row):
            if ch == "X":
                for dy in range(scale_y):
                    for dx in range(scale_x):
                        px = off_x + gx * scale_x + dx
                        py = off_y + gy * scale_y + dy
                        if 0 <= px < size and 0 <= py < size:
                            pixels[py * size + px] = fg_rgb

    # Encode as PNG
    def chunk(name: bytes, data: bytes) -> bytes:
        raw = name + data
        return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))

    raw_rows = b""
    for row_i in range(size):
        raw_rows += b"\x00"  # filter byte (None)
        for col_i in range(size):
            raw_rows += bytes(pixels[row_i * size + col_i])

    idat = chunk(b"IDAT", zlib.compress(raw_rows, 9))
    iend = chunk(b"IEND", b"")

    return sig + ihdr + idat + iend


def main():
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(icons_dir, exist_ok=True)

    for size in (16, 48, 128):
        path = os.path.join(icons_dir, f"icon{size}.png")
        data = make_png(size)
        with open(path, "wb") as f:
            f.write(data)
        print(f"  ✓  icons/icon{size}.png  ({len(data)} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()
