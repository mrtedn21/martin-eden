import json
from utils import get_string_of_model
from core import CustomSchema, CustomJsonSchema
from datetime import date, datetime

from marshmallow import Schema

SCHEMA_PATH_TEMPLATE = '#/components/schemas/{}'

with open('example.json') as file:
    openapi_object = json.load(file)

defined_marshmallow_schemas = {}

type_map_to_string = {
    str: 'string',
    int: 'integer',
    datetime: 'string',
    date: 'string',
}


def dict_set(dct: dict, path: str, value):
    keys = path.split('.')
    keys_except_last = keys[:-1]
    last_key = keys[-1]

    for key in keys_except_last:
        dct = dct.setdefault(key, {})

    dct[last_key] = value
    return dct[last_key]


def register_marshmallow_schema(schema: CustomSchema):
    if not schema:
        return

    default_name = type(schema).__name__
    defined_name = schema.json_schema_name
    defined_marshmallow_schemas[defined_name or default_name] = schema


def change_openapi_schema_root(dct):
    for key, value in dct.items():
        if key == '$ref':
            dct[key] = value.replace('definitions', 'components/schemas')
        if isinstance(value, dict):
            change_openapi_schema_root(value)


def write_pydantic_models_to_openapi():
    json_schema = CustomJsonSchema()
    resulting_schema = {}
    for schema in defined_marshmallow_schemas.values():
        resulting_schema.update(json_schema.dump(schema))

    definitions = resulting_schema['definitions']
    change_openapi_schema_root(definitions)

    for schema in definitions.values():
        schema.pop('additionalProperties', None)
    openapi_object['components']['schemas'] = definitions


def set_response_for_openapi_method(
    openapi_method: dict, schema=None,
):
    if not schema:
        return

    response_schema = dict_set(
        openapi_method, 'responses.200.content.application/json.schema', {},
    )
    if schema.many:
        response_schema['type'] = 'array'
        response_schema['items'] = {
            '$ref': SCHEMA_PATH_TEMPLATE.format(schema.json_schema_name),
        }
    else:
        response_schema['$ref'] = SCHEMA_PATH_TEMPLATE.format(
            schema.json_schema_name,
        )


def set_request_for_openapi_method(
    openapi_method: dict, schema: CustomSchema = None,
):
    if schema and isinstance(schema, CustomSchema):
        request_schema = dict_set(
            openapi_method, 'requestBody.content.application/json.schema',
            {},
        )
        schema_path = SCHEMA_PATH_TEMPLATE.format(schema.json_schema_name)
        request_schema['$ref'] = schema_path


def set_query_params(openapi_method: dict, query_params: dict) -> None:
    if not query_params:
        return

    parameters = openapi_method.setdefault('parameters', [])
    for model_obj, fields in query_params.items():
        for field in fields:
            param_type = type_map_to_string[
                getattr(model_obj, field).type.python_type
            ]
            model_name = get_string_of_model(model_obj)
            if param_type == 'string':
                method_name = 'like'
            else:
                method_name = 'in'

            parameters.append({
                'name': f'{model_name}__{field}__{method_name}',
                'in': 'query',
                'schema': {'type': param_type},
            })


def add_openapi_path(
    path: str, method: str, request_schema: Schema = None, response_schema: Schema = None, query_params: dict = None,
):
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

    register_marshmallow_schema(response_schema)
    set_response_for_openapi_method(openapi_new_method, response_schema)

    register_marshmallow_schema(request_schema)
    set_request_for_openapi_method(openapi_new_method, request_schema)

    set_query_params(openapi_new_method, query_params)