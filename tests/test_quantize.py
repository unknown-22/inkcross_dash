from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.quantize import HEIGHT, WIDTH, to_4level_bmp


def test_to_4level_bmp_outputs_480x800_bmp_with_four_bit_depth() -> None:
    source = Image.new("RGB", (120, 200), "white")
    bmp = to_4level_bmp(source)

    assert bmp[:2] == b"BM"
    assert len(bmp) == 192118
    assert int.from_bytes(bmp[18:22], "little", signed=True) == WIDTH
    assert abs(int.from_bytes(bmp[22:26], "little", signed=True)) == HEIGHT
    assert int.from_bytes(bmp[28:30], "little") == 4

    with Image.open(BytesIO(bmp)) as image:
        assert image.size == (WIDTH, HEIGHT)
        assert image.mode == "P"
        assert set(image.tobytes()) <= {0, 1, 2, 3}
