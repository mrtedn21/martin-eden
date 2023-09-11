import json
from types import GenericAlias
from typing import Callable

from pydantic import BaseModel

SCHEMA_PATH_TEMPLATE = '#/components/schemas/{}'

with open('example.json') as file:
    openapi_object = json.load(file)


def dict_set(dct: dict, path: str, value):
    keys = path.split('.')
    keys_except_last = keys[:-1]
    last_key = keys[-1]

    for key in keys_except_last:
        dct = dct.setdefault(key, {})

    dct[last_key] = value
    return dct[last_key]


def add_openapi_schema(name: str, model: BaseModel):
    openapi_object['components']['schemas'][name] = model.model_json_schema()


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
    elif issubclass(return_annotation, BaseModel):
        response_schema['$ref'] = SCHEMA_PATH_TEMPLATE.format(
            return_annotation.__name__,
        )


def set_request_for_openapi_method(openapi_method: dict, controller: Callable):
    for arg_type in controller.__annotations__.values():
        if issubclass(arg_type, BaseModel):
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
    openapi_new_method['operationId'] = (
        path.replace('/', '') + '_' + method.lower(),
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
        if issubclass(inner_type, BaseModel):
            return list, inner_type
