import json
from types import GenericAlias
from typing import Callable
from marshmallow_jsonschema import JSONSchema

from marshmallow import Schema

SCHEMA_PATH_TEMPLATE = '#/components/schemas/{}'

with open('example.json') as file:
    openapi_object = json.load(file)

defined_marshmallow_schemas = {}


def dict_set(dct: dict, path: str, value):
    keys = path.split('.')
    keys_except_last = keys[:-1]
    last_key = keys[-1]

    for key in keys_except_last:
        dct = dct.setdefault(key, {})

    dct[last_key] = value
    return dct[last_key]


def register_marshmallow_schema(name: str, schema: Schema):
    defined_marshmallow_schemas[name] = schema


def change_openapi_schema_root(dct):
    for key, value in dct.items():
        if key == '$ref':
            dct[key] = value.replace('definitions', 'components/schemas')
        if isinstance(value, dict):
            change_openapi_schema_root(value)


def write_pydantic_models_to_openapi():
    json_schema = JSONSchema()
    resulting_schema = {}
    for schema in defined_marshmallow_schemas.values():
        resulting_schema.update(json_schema.dump(schema()))

    definitions = resulting_schema['definitions']
    change_openapi_schema_root(definitions)

    for schema in definitions.values():
        schema.pop('additionalProperties', None)
    openapi_object['components']['schemas'] = definitions


def set_response_for_openapi_method(
    openapi_method: dict, controller: Callable,
):
    return_annotation = controller.__annotations__.pop('return', None)
    if not return_annotation:
        return

    response_schema = dict_set(
        openapi_method, 'responses.200.content.application/json.schema', {},
    )
    if type(return_annotation) == GenericAlias:
        outer_type, inner_type = parse_complex_annotation(return_annotation)
        response_schema['type'] = 'array'
        response_schema['items'] = {
            '$ref': SCHEMA_PATH_TEMPLATE.format(inner_type.__name__),
        }
    elif issubclass(return_annotation, Schema):
        response_schema['$ref'] = SCHEMA_PATH_TEMPLATE.format(
            return_annotation.__name__,
        )


def set_request_for_openapi_method(openapi_method: dict, controller: Callable):
    for arg_type in controller.__annotations__.values():
        if issubclass(arg_type, Schema):
            request_schema = dict_set(
                openapi_method, 'requestBody.content.application/json.schema',
                {},
            )
            schema_path = SCHEMA_PATH_TEMPLATE.format(arg_type.__name__)
            request_schema['$ref'] = schema_path


def add_openapi_path(path: str, method: str, controller: Callable):
    # in the framework /schema/ is used for openapi, therefore no need
    # create openapi description of method that create openapi schema
    if path == '/schema/':
        return

    openapi_new_method = dict_set(
        openapi_object,
        f'paths.{path}.{method}',
        {},
    )
    # IMPORTANT. In this brackets can't be comma, with comma
    # operationId will be tuple, but must be string
    openapi_new_method['operationId'] = (
        path.replace('/', '') + '_' + method.lower()
    )

    set_response_for_openapi_method(openapi_new_method, controller)
    set_request_for_openapi_method(openapi_new_method, controller)


def parse_complex_annotation(annotation: GenericAlias) -> tuple[type, type]:
    """If annotation is complex type hint, like list[UserGetModel], then
    the function will return outer type and inner type. In example
    with list[UserGetModel] return types will be list and UserGetModel.
    """
    # annotation() is initialize its outer type
    if isinstance(annotation(), list):
        # There are inner types in annotation.__args__
        inner_type = annotation.__args__[0]
        if issubclass(inner_type, Schema):
            return list, inner_type
