"""Generate a simple icon.ico for Drama Reels."""
import struct
import os

def create_icon():
    """Create a 64x64 ICO file with a red play button on dark background."""
    size = 64

    # Create pixel data (BGRA format)
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            # Center the design
            cx, cy = x - size // 2, y - size // 2
            dist = (cx * cx + cy * cy) ** 0.5

            # Background: dark circle
            if dist < 28:
                # Red play button triangle
                nx = x / size
                ny = y / size
                # Triangle shape (pointing right)
                if (0.35 < nx < 0.7) and (0.25 < ny < 0.75):
                    # Check if inside triangle
                    tx = (nx - 0.35) / 0.35
                    ty_center = 0.5
                    half_height = 0.25 * (1 - abs(tx - 0.5) * 2)
                    if abs(ny - ty_center) < half_height:
                        pixels.extend([0, 0, 230, 255])  # Red
                    else:
                        pixels.extend([20, 20, 30, 255])  # Dark bg
                else:
                    pixels.extend([20, 20, 30, 255])  # Dark bg
            elif dist < 30:
                pixels.extend([100, 50, 50, 255])  # Border
            else:
                pixels.extend([0, 0, 0, 0])  # Transparent

    # ICO header
    ico_header = struct.pack('<HHH', 0, 1, 1)  # Reserved, Type=ICO, Count=1

    # ICO directory entry
    bpp = 32
    image_size = size * size * (bpp // 8)
    bmp_size = 40 + image_size + (size * size // 8)  # BMP header + pixels + AND mask
    ico_entry = struct.pack('<BBBBHHII',
        size if size < 256 else 0,  # Width
        size if size < 256 else 0,  # Height
        0,   # Color count (0 for 32-bit)
        0,   # Reserved
        1,   # Color planes
        bpp, # Bits per pixel
        bmp_size,  # Image size
        22   # Offset to image data
    )

    # BMP info header
    bmp_header = struct.pack('<IiiHHIIiiII',
        40,           # Header size
        size,         # Width
        size * 2,     # Height (doubled for ICO)
        1,            # Color planes
        bpp,          # Bits per pixel
        0,            # Compression (none)
        image_size,   # Image size
        0, 0,         # Pixels per meter
        0, 0          # Colors
    )

    # AND mask (all zeros = fully visible)
    and_mask = bytearray(size * (size // 8))

    # Write ICO file
    os.makedirs('scripts', exist_ok=True)
    with open('icon.ico', 'wb') as f:
        f.write(ico_header)
        f.write(ico_entry)
        f.write(bmp_header)
        f.write(bytes(pixels))
        f.write(bytes(and_mask))

    print(f"Created icon.ico ({os.path.getsize('icon.ico')} bytes)")

if __name__ == '__main__':
    create_icon()
