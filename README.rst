+++++++++++++++
Strictus Dictus
+++++++++++++++

.. code-block:: shell

    pip install strictus-dictus


``StrictusDictus`` (aka ``sdict``) is a base class for special ``dict`` sub-classes, instances of which only accept
keys that are declared in the class's type hints.

This is useful for data transfer object definitions, for example, when you are expressing someone else's
JSON or YAML schema in your code and want to access the contents of the parsed dictionaries using dot notation
and have your IDE auto-complete the attribute names.

``sdict`` is suitable for nested structures.

.. code-block:: python

    from strictus_dictus import sdict

    class Header(sdict):
        title: str = "Hello, world!"  # default value
        sent: str

    class Tag(sdict):
        value: str

    class Message(sdict):
        header: Header
        body: str
        tags: List[Tag]

    source = {
        "header": {
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

    # It still is a dictionary so this works too:
    assert message["header"]["title"] == "Hello, world!"

    # Convert back to a standard dictionary
    message.to_dict()


The values of these keys are accessible as attributes with dot notation as well as with ``[]`` notation,
however, if the source dictionary is missing the key, ``StrictusDictus`` will not introduce it so access
via ``[]`` notation will raise a ``KeyError`` as expected.
However, the attribute will be initialised to hold the special ``EMPTY`` value.

To create an instance use ``YourClass(standard_dict)`` and to export to a standard dictionary
use ``YourClass().to_dict()``.

Only a limited set of type hints are supported by ``StrictusDictus``. Unsupported type hints will
be silently ignored and values will be returned unprocessed.

Supported type hints are (``SD`` denotes any class inheriting from ``StrictusDictus``):


.. code-block:: python

    class Examples:
        x1: primitive_type  # could be any type, but not from typing.*; value won't be processed
        x2: List  # unprocessed list
        x3: Dict  # unprocessed dictionary
        x4: SD
        x5: List[SD]
        x6: Dict[str, SD]


You can annotate x with ``List[Any]`` and ``Dict[Any, Any]``, but the values won't be processed
by ``StrictusDictus``.

Limitations
-----------

* An ``sdict`` sub-class cannot reference itself in its type hints (not even with forward references).


Dataclasses?
------------

Dataclass is a great building block, but it doesn't treat dictionaries seriously.

.. code-block:: python

    @dataclasses.dataclass
    class Point:
        x: float
        y: float

    @dataclasses.dataclass
    class Line:
        start: Point
        end: Point

    line = Line(**{"start": {"x": 1, "y": 1}, "end": {"x": 5, "y": 5}})

I would expect ``line.end.y`` to hold value ``5`` , but that's not the case. In fact, ``print(line.end.y)``
raises an ``AttributeError``:

.. code-block:: python

    AttributeError: 'dict' object has no attribute 'y'

