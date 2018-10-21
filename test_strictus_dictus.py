from typing import Dict, List, Optional, Sequence, Union

import pytest

from strictus_dictus import EMPTY, StrictusDictus


class Point(StrictusDictus):
    x: int
    y: int


class Line(StrictusDictus):
    start: Point
    end: Point


class Cloud(StrictusDictus):
    points: List[Point]
    edges: Dict[str, Point]


def test_instantiating_sd_base_class_raises_type_error():
    with pytest.raises(TypeError) as exc_info:
        StrictusDictus()
    assert "StrictusDictus is an abstract base class" in str(exc_info.value)


def test_sd_is_a_dict():
    assert isinstance(Point(), StrictusDictus)
    assert isinstance(Point(), dict)


def test_sd_dotnotation_access():
    p = Point(x=-1)
    assert p.x == -1
    assert p.y is EMPTY


def test_sd_getitem_access():
    p = Point(x=-1)
    assert p["x"] == -1
    assert "y" not in p


def test_keys_are_validated_on_creation():
    with pytest.raises(ValueError) as exc_info:
        Point(z=5)
    assert "Unsupported key(s)" in str(exc_info.value)


def test_empty_composite_sd():
    line = Line()
    assert isinstance(line, Line)
    assert line.start is EMPTY
    assert line.end is EMPTY
    assert line.to_dict() == {}


def test_non_empty_composite_sd():
    line = Line({"start": {"x": 3, "y": 4}})
    assert isinstance(line.start, Point)
    assert line.end is EMPTY
    assert line.start.x == 3
    assert line.start.y == 4
    assert isinstance(line.start, Point)
    assert line.to_dict() == {"start": {"x": 3, "y": 4}}
    assert not isinstance(line.to_dict()["start"], Point)
    assert isinstance(line.to_dict()["start"], dict)


def test_undefined_container_initialised_as_empty():
    cloud = Cloud()
    assert cloud.points is EMPTY
    assert cloud.to_dict() == {}


def test_list_of_sd_parsed():
    cloud = Cloud(points=[{"x": 1, "y": 1}, {"x": 2, "y": 2}])
    assert len(cloud.points) == 2
    assert isinstance(cloud.points[0], Point)
    assert cloud.points[1].x == 2
    assert cloud.points[1].y == 2
    assert cloud.to_dict() == {"points": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]}


def test_dict_of_sd_parsed():
    source = {
        "edges": {
            "topleft": {"x": -5, "y": 5},
            "bottomleft": {"x": 3, "y": -3},
        }
    }
    cloud = Cloud(**source)
    assert isinstance(cloud.edges, dict)
    assert isinstance(cloud.edges["topleft"], Point)
    assert cloud.edges["topleft"].x == -5
    assert cloud.to_dict() == source

    assert not isinstance(cloud.to_dict()["edges"]["topleft"], Point)
    assert isinstance(cloud.to_dict()["edges"]["topleft"], dict)


@pytest.mark.parametrize('type_hint', [
    Sequence,
    Sequence[int],
    Optional[int],
    Union[int, str],
    Dict[str, int],
])
def test_unsupported_type_hints_leave_value_unprocessed(type_hint):
    x = object()

    class Weird(StrictusDictus):
        x: type_hint

    weird = Weird(x=x)
    assert weird.x is x

    assert weird.to_dict() == {"x": x}


def test_readme_example():
    from strictus_dictus import StrictusDictus

    class Header(StrictusDictus):
        title: str
        sent: str

    class Tag(StrictusDictus):
        value: str

    class Message(StrictusDictus):
        header: Header
        body: str
        tags: List[Tag]

    source = {
        "header": {
            "title": "Hello, world!",
            "sent": "2018-10-20 18:09:42",
        },
        "body": "What is going on?",
        "tags": [
            {
                "value": "unread",
            },
        ],
    }

    # Parse the message
    message = Message(source)

    # Access attributes
    assert message.header.title == "Hello, world!"
    assert message.tags[0].value == "unread"

    # Convert back to a standard dictionary
    message.to_dict()
