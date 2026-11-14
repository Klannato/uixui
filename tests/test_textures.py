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
