from uispec.textures import PATTERN_SIZE, pattern_tile


def _alpha(img, x, y):
    return img.pixelColor(x, y).alpha()


def test_repeating_patterns_are_seamless():
    # These rules repeat every 16 pixels, which divides the tile size, so tiles meet without seams.
    for name in ("stripes", "hatch", "dots"):
        img = pattern_tile(name, "#ff0000")
        assert img.width() == PATTERN_SIZE and img.height() == PATTERN_SIZE
        for x in range(PATTERN_SIZE - 16):
            for y in range(PATTERN_SIZE - 16):
                assert _alpha(img, x, y) == _alpha(img, x + 16, y), name
                assert _alpha(img, x, y) == _alpha(img, x, y + 16), name


def test_pattern_uses_requested_color():
    img = pattern_tile("dots", "#00ff00")
    colored = [img.pixelColor(x, y) for x in range(PATTERN_SIZE) for y in range(PATTERN_SIZE)
               if img.pixelColor(x, y).alpha() > 0]
    assert colored and all(c.green() == 255 and c.red() == 0 for c in colored)


def test_unknown_pattern_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        pattern_tile("waves", "#000000")


def test_baked_pattern_scales_and_folds_opacity(qapp):
    from uispec.textures import baked_image

    img = baked_image({"kind": "pattern", "pattern": "dots", "color": "#ffcc00",
                       "scale": 2.0, "opacity": 0.5}, None)
    assert (img.width(), img.height()) == (128, 128)
    assert max(memoryview(img.bits())[3::4]) == 95


def test_baked_image_keeps_natural_size_and_applies_tint(qapp, sample_png):
    from uispec.textures import baked_image

    img = baked_image({"kind": "image", "file": str(sample_png), "mode": "stretch",
                       "opacity": 1.0, "tint": "#3366ff"}, sample_png.parent)
    assert (img.width(), img.height()) == (400, 300)
    c = img.pixelColor(10, 10)
    assert (c.red(), c.green(), c.blue(), c.alpha()) == (0x33, 0x66, 0xFF, 255)
