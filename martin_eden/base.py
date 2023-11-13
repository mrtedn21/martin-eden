from typing import Any, ParamSpecArgs, ParamSpecKwargs

from marshmallow import Schema
from marshmallow.decorators import post_dump
from marshmallow_jsonschema import JSONSchema


class Controller:
    """The class needs only as type hint"""
    request_schema: Schema
    response_schema: Schema
    query_params: dict

    def __call__(
        self, *args: ParamSpecArgs, **kwargs: ParamSpecKwargs,
    ) -> None:
        pass

    def __await__(self):
        pass


class CustomSchema(Schema):
    def __init__(
        self,
        *args: ParamSpecArgs,
        json_schema_name: str = None,
        **kwargs: ParamSpecKwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.json_schema_name = json_schema_name
        self.__name__ = json_schema_name


class CustomJsonSchema(JSONSchema):
    @post_dump
    def wrap(self, data: dict, **_) -> dict[str, Any]:
        """Wrap this with the root schema definitions."""
        if self.nested:  # no need to wrap, will be in outer defs
            return data

        schema_name = self.obj.json_schema_name

        data["additionalProperties"] = False

        self._nested_schema_classes[schema_name] = data
        root = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self._nested_schema_classes,
            "$ref": f"#/definitions/{schema_name}",
        }
        return root