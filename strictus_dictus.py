from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple, Type, get_type_hints  # noqa

import dataclasses
import typing_inspect


class _Empty:
    def __bool__(self):
        return False

    def __repr__(self):
        return 'EMPTY'


EMPTY = _Empty()


def _get_attr(instance, name):
    if name in instance:
        return instance[name]
    elif name in instance._strictus_dictus_schema:
        return instance._strictus_dictus_schema[name].value
    raise AttributeError(name)


def _create_getter(name) -> Callable:

    def getter(instance):
        return _get_attr(instance, name)

    getter.__name__ = name
    return getter


class StrictusDictus(dict):
    """
    StrictusDictus is a base class for special dict sub-classes, instances of which only accepts keys that
    are declared in the class's type hints.
    The values of these keys are accessible as attributes with dot notation as well as with [] notation,
    however, if the source dictionary is missing the key, StrictusDictus will not introduce it so access
    via [] notation will raise a KeyError.
    However, the attribute will be initialised to hold the special EMPTY value.

    To create an instance use YourClass(standard_dict) and to export to a standard dictionary
    use YourClass().to_dict().

    Only a limited set of type hints are supported by StrictusDictus. Unsupported type hints will
    be silently ignored and values will be returned unprocessed.

    Given x, an attribute of StrictusDictus, supported type hints are (SD denotes any class
    inheriting from StrictusDictus):

        x: primitive_type (could be any type, but not from typing.*; value won't be processed)
        x: List (unprocessed list)
        x: Dict (unprocessed dictionary)
        x: SD
        x: List[SD]
        x: Dict[str, SD]

    You can annotate x with ``List[Any]`` and ``Dict[Any, Any]``, but the values won't be processed
    by StrictusDictus.

    A StrictusDictus class cannot reference itself in its type hints (not even with forward references).
    """

    _strictus_dictus_schema: Dict  # type: ClassVar[Dict[str, "StrictusDictus._SchemaItem"]]

    def __init__(self, *args, **kwargs):
        if self.__class__ is StrictusDictus:
            raise TypeError(f"{self.__class__.__name__} is an abstract base class and should not be instantiated.")
        parsed = self._parse(dict(*args, **kwargs))
        super().__init__(**parsed)

    @dataclasses.dataclass
    class _SchemaItem:
        name: str
        type: Type
        value: Any = EMPTY

        type_str: str = dataclasses.field(default=None, init=False)
        is_typing: bool = dataclasses.field(default=None, init=False)
        is_list: bool = dataclasses.field(default=None, init=False)
        is_dict: bool = dataclasses.field(default=None, init=False)
        typing_args: Tuple = dataclasses.field(default=None, init=False)
        is_strictus_dictus: bool = dataclasses.field(default=None, init=False)
        is_container_of_strictus_dictus: bool = dataclasses.field(default=None, init=False)

        def __post_init__(self):
            self.type_str = str(self.type)
            self.is_typing = self.type_str.startswith("typing.")
            self.is_list = self.type_str.startswith("typing.List")
            self.is_dict = self.type_str.startswith("typing.Dict")
            self.typing_args = typing_inspect.get_args(self.type)
            self.is_strictus_dictus = is_strictus_dictus(self.type)
            self.is_container_of_strictus_dictus = (
                (self.is_list and self.typing_args and is_strictus_dictus(self.typing_args[0])) or
                (self.is_dict and self.typing_args and is_strictus_dictus(self.typing_args[1]))
            )

    def __init_subclass__(cls, **kwargs):
        strictus_dictus_schema = {}

        parent_schema = {}
        if hasattr(cls, "_strictus_dictus_schema"):
            parent_schema = getattr(cls, "_strictus_dictus_schema")

        for k, v in get_type_hints(cls).items():
            if k == "_strictus_dictus_schema":
                continue
            if str(v).startswith("typing.ClassVar"):
                continue
            if hasattr(cls, k):
                default_value = getattr(cls, k)
            elif k in parent_schema:
                default_value = parent_schema[k].value
            else:
                default_value = EMPTY
            strictus_dictus_schema[k] = StrictusDictus._SchemaItem(name=k, type=v, value=default_value)
            if default_value is not EMPTY:
                # We need to remove or replace the attribute from the class because its presence will
                # stop __getattr__ from being called.
                if k in cls.__dict__:
                    # We can safely only remove the attribute from the class itself, but not from its parents.
                    delattr(cls, k)
                else:
                    # Override the attribute
                    setattr(cls, k, property(_create_getter(k)))

        cls._strictus_dictus_schema = strictus_dictus_schema

    __getattr__ = _get_attr

    def to_dict(self):
        """
        Convert an instance of StrictusDictus into a standard dictionary with all nested StrictusDictus
        also converted to dictionaries.
        """

        if hasattr(self, "Meta"):
            meta = self.Meta.__dict__
        else:
            meta = {}
        allow_additional_attributes = meta.get("additional_attributes", False)

        export = {}
        for item in self._strictus_dictus_schema.values():  # type: StrictusDictus._SchemaItem
            if item.name not in self:
                continue

            value = self[item.name]
            if value is None:
                export[item.name] = value
                continue

            # If value.to_dict() or v.to_dict() below fails because value or v is not a StrictusDictus,
            # you must have obtained an invalid instance of StrictusDictus and the problem most likely
            # lies in the parser.

            if item.is_strictus_dictus:
                export[item.name] = value.to_dict()

            elif item.is_container_of_strictus_dictus:
                if item.is_list:
                    export[item.name] = [v.to_dict() for v in value]
                else:
                    assert item.is_dict
                    export[item.name] = {k: v.to_dict() for k, v in value.items()}

            else:
                if isinstance(item.type, type) and value is not None:
                    if issubclass(item.type, str):
                        # Convert to primitive string
                        value = str(value)

                    elif issubclass(item.type, int):
                        value = int(value)

                    elif issubclass(item.type, float):
                        value = float(value)

                    elif issubclass(item.type, bool):
                        value = bool(value)

                export[item.name] = value

        if allow_additional_attributes:
            export.update((k, self[k]) for k in self if k not in export)

        return export

    @classmethod
    def _parse(cls, dct: Dict) -> Optional[Dict]:
        if dct is None:
            return dct

        if hasattr(cls, "Meta"):
            meta = cls.Meta.__dict__
        else:
            meta = {}
        allow_additional_attributes = meta.get("additional_attributes", False)

        empties = set()
        parsed = {}
        for item in cls._strictus_dictus_schema.values():  # type: StrictusDictus._SchemaItem
            if item.name in dct:
                raw_value = dct[item.name]
                if raw_value is EMPTY:
                    empties.add(item.name)
                elif raw_value is None:
                    parsed[item.name] = raw_value
                elif item.is_strictus_dictus:
                    parsed[item.name] = item.type(raw_value)
                elif item.is_dict:
                    parsed[item.name] = cls._parse_generic_dict(item, raw_value)
                elif item.is_list:
                    parsed[item.name] = cls._parse_generic_list(item, raw_value)
                elif item.type in (int, float):
                    if raw_value == "":
                        parsed[item.name] = None
                    else:
                        parsed[item.name] = item.type(raw_value)
                elif item.type is str:
                    parsed[item.name] = item.type(raw_value)
                else:
                    parsed[item.name] = raw_value
            elif item.value is not EMPTY:
                parsed[item.name] = item.value

        if allow_additional_attributes:
            parsed.update((k, dct[k]) for k in dct if (k not in parsed and k not in empties))
        else:
            unknown = {repr(k) for k in dct if (k not in parsed and k not in empties)}
            if unknown:
                raise ValueError(f"Unsupported key(s) {', '.join(unknown)} passed to {cls.__name__}")
        return parsed

    @classmethod
    def _parse_generic_dict(cls, item: "StrictusDictus._SchemaItem", value: Optional[Dict]) -> Optional[Dict]:
        if value is None:
            return value
        type_args = typing_inspect.get_args(item.type)
        if not type_args:
            return value
        else:
            if isinstance(type_args[1], type) and issubclass(type_args[1], StrictusDictus) and isinstance(value, dict):
                return {k: type_args[1](v) for k, v in value.items()}
            return value

    @classmethod
    def _parse_generic_list(cls, item: "StrictusDictus._SchemaItem", value: Optional[List]) -> Optional[Dict]:
        if value is None:
            return value
        type_args = typing_inspect.get_args(item.type)
        if not type_args:
            return value
        else:
            if isinstance(type_args[0], type) and issubclass(type_args[0], StrictusDictus):
                return [type_args[0](x) for x in value]
            return value


def is_strictus_dictus(instance_or_type: Any) -> bool:
    if isinstance(instance_or_type, type):
        return issubclass(instance_or_type, StrictusDictus)
    return isinstance(instance_or_type, StrictusDictus)


sdict = StrictusDictus


def get_schema(instance_or_type: Any):
    """
    Returns schema of the StrictusDictus instance or class.
    """
    assert is_strictus_dictus(instance_or_type)
    return instance_or_type._strictus_dictus_schema


__all__ = [
    "EMPTY",
    "StrictusDictus",
    "sdict",
    "get_schema",
]
