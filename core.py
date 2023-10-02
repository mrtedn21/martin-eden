import datetime
import decimal
import uuid
from enum import Enum
from inspect import isclass
import typing
from marshmallow_jsonschema.base import _resolve_additional_properties

from marshmallow import fields, missing, Schema, validate
from marshmallow.class_registry import get_class
from marshmallow.decorators import post_dump
from marshmallow.utils import _Missing

from marshmallow import INCLUDE, EXCLUDE, RAISE

try:
    from marshmallow_union import Union

    ALLOW_UNIONS = True
except ImportError:
    ALLOW_UNIONS = False

try:
    from marshmallow_enum import EnumField, LoadDumpOptions

    ALLOW_ENUMS = True
except ImportError:
    ALLOW_ENUMS = False

from marshmallow_jsonschema import JSONSchema


class CustomSchema(Schema):
    def __init__(self, *args, json_schema_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_schema_name = json_schema_name
        self.__name__ = json_schema_name


class CustomJsonSchema(JSONSchema):
    @post_dump
    def wrap(self, data, **_) -> typing.Dict[str, typing.Any]:
        """Wrap this with the root schema definitions."""
        if self.nested:  # no need to wrap, will be in outer defs
            return data

        schema_name = self.obj.json_schema_name

        data["additionalProperties"] = False

        self._nested_schema_classes[schema_name] = data
        root = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self._nested_schema_classes,
            "$ref": "#/definitions/{name}".format(name=schema_name),
        }
        return root
