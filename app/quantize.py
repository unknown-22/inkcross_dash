from __future__ import annotations

import io
import struct

from PIL import Image

WIDTH = 480
HEIGHT = 800
GRAYSCALE_PALETTE = [
    0,
    0,
    0,
    85,
    85,
    85,
    170,
    170,
    170,
    255,
    255,
    255,
] + [0] * (256 - 4) * 3


def to_4level_bmp(image: Image.Image) -> bytes:
    resized = image.convert("RGB").resize((WIDTH, HEIGHT))
    quantized = quantize_4level_floyd_steinberg(resized.convert("L"))
    return encode_4bit_bmp(quantized)


def quantize_4level_floyd_steinberg(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    width, height = gray.size
    source = gray.tobytes()
    output = bytearray(width * height)
    current_errors = [0.0] * (width + 2)
    next_errors = [0.0] * (width + 2)

    for y in range(height):
        for x in range(width):
            offset = y * width + x
            value = min(255.0, max(0.0, source[offset] + current_errors[x + 1]))
            index = min(3, max(0, round(value / 85)))
            quantized = index * 85
            output[offset] = index
            error = value - quantized
            current_errors[x + 2] += error * 7 / 16
            next_errors[x] += error * 3 / 16
            next_errors[x + 1] += error * 5 / 16
            next_errors[x + 2] += error * 1 / 16
        current_errors, next_errors = next_errors, [0.0] * (width + 2)

    result = Image.frombytes("P", (width, height), bytes(output))
    result.putpalette(GRAYSCALE_PALETTE)
    return result


def encode_4bit_bmp(image: Image.Image) -> bytes:
    if image.mode != "P":
        raise ValueError("4bit BMP encoding requires a palette image")

    width, height = image.size
    row_size = ((width * 4 + 31) // 32) * 4
    pixel_array_size = row_size * height
    palette_size = 16 * 4
    pixel_offset = 14 + 40 + palette_size
    file_size = pixel_offset + pixel_array_size

    buffer = io.BytesIO()
    buffer.write(b"BM")
    buffer.write(struct.pack("<IHHI", file_size, 0, 0, pixel_offset))
    buffer.write(
        struct.pack(
            "<IiiHHIIiiII",
            40,
            width,
            height,
            1,
            4,
            0,
            pixel_array_size,
            2835,
            2835,
            16,
            0,
        )
    )
    for gray in (0, 85, 170, 255):
        buffer.write(bytes((gray, gray, gray, 0)))
    buffer.write(bytes((0, 0, 0, 0)) * 12)

    pixels = image.tobytes()
    for y in range(height - 1, -1, -1):
        row = bytearray()
        for x in range(0, width, 2):
            offset = y * width + x
            left = pixels[offset] & 0x0F
            right = pixels[offset + 1] & 0x0F if x + 1 < width else 0
            row.append((left << 4) | right)
        row.extend(b"\x00" * (row_size - len(row)))
        buffer.write(row)

    return buffer.getvalue()
