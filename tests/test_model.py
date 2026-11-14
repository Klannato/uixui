from uispec.model import Arrow, Project, Screen


def make_screen():
    s = Screen(name="Login", image="screens/01-login.png")
    for i in range(3):
        s.add_element("rect", [[i * 10, 0], [i * 10 + 5, 5]])
    return s


def test_delete_renumbers_elements_and_arrows():
    s = make_screen()
    s.arrows.append(Arrow(from_number=3, to_number=1, label="x"))
    s.delete_element(2)
    assert [e.number for e in s.elements] == [1, 2]
    assert s.arrows[0].from_number == 2
    assert s.arrows[0].to_number == 1


def test_delete_removes_arrows_touching_element():
    s = make_screen()
    s.arrows.append(Arrow(from_number=2, to_number=3))
    s.delete_element(2)
    assert s.arrows == []


def test_round_trip_keeps_everything():
    p = Project(name="App", screens=[make_screen()])
    p.screens[0].leads_to = "Home"
    p.screens[0].elements[0].states = ["default", "hover"]
    again = Project.from_dict(p.to_dict())
    assert again.to_dict() == p.to_dict()


def test_missing_fields_reports_name_and_purpose():
    s = make_screen()
    assert s.elements[0].missing_fields() == ["name", "purpose"]


def test_resize_rect_keeps_two_corners():
    from uispec.model import Element

    e = Element(number=1, kind="rect", points=[[10, 10], [60, 40]])
    e.resize(10, 10, 110, 90)
    assert e.points == [[10, 10], [110, 90]]
    assert e.bbox() == (10, 10, 110, 90)


def test_resize_freehand_scales_every_point():
    from uispec.model import Element

    e = Element(number=1, kind="freehand", points=[[0, 0], [50, 0], [50, 100]])
    e.resize(0, 0, 100, 50)
    assert e.points == [[0, 0], [100, 0], [100, 50]]


def test_resize_rejects_tiny_boxes():
    import pytest
    from uispec.model import Element

    e = Element(number=1, kind="rect", points=[[0, 0], [20, 20]])
    with pytest.raises(ValueError):
        e.resize(0, 0, 2, 20)
