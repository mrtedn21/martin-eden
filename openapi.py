import json
from datetime import date, datetime

from marshmallow import Schema

from core import CustomJsonSchema, CustomSchema
from utils import get_name_of_model, dict_set


class OpenApiBuilder:
    _instance = None
    SCHEMA_PATH_TEMPLATE = '#/components/schemas/{}'

    def __new__(cls):
        """This method makes from OpenApiBuilder - singleton"""
        if cls._instance is None:
            cls._instance = super(OpenApiBuilder, cls).__new__(cls)
            cls.defined_marshmallow_schemas = set()
            with open('example.json') as file:
                cls.openapi_object = json.load(file)
        return cls._instance

    @staticmethod
    def python_type_to_string_map(python_type):
        mapping = {
            str: 'string',
            int: 'integer',
            datetime: 'string',
            date: 'string',
        }
        return mapping[python_type]

    def register_marshmallow_schema(self, schema: CustomSchema):
        """Register schemas for openapi doc - using concrete
        instance of marshmallow schema. Not class of marshmallow
        schema, but instance, because it is more flexible"""
        if schema:
            self.defined_marshmallow_schemas.add(schema)

    def change_definitions_references(self, dct: dict):
        """JSON Schemas defined with marshmallow_jsonschema library,
        all, include nested schemas, are placed in root of dictionary,
        therefore, if some schema have nested schema, it uses reference.
        By default, reference has path: '#/definitions/SomeSchema',
        but for openapi doc, path must be: '#/components/schemas/SomeSchema'.
        And the method replace default path to correct for openapi doc path"""
        for key, value in dct.items():
            if key == '$ref':
                dct[key] = value.replace('definitions', 'components/schemas')
            if isinstance(value, dict):
                self.change_definitions_references(value)

    def write_marshmallow_schemas_to_openapi_doc(self):
        """The method writes all registered schemas to openapi documentation"""
        marshmallow_json_schemas = self.generate_json_schemas()
        self.change_definitions_references(marshmallow_json_schemas)
        result_json_schemas = self.clean_schemas_from_additional_properties(
            marshmallow_json_schemas
        )
        self.openapi_object['components']['schemas'] = result_json_schemas

    @staticmethod
    def clean_schemas_from_additional_properties(schemas: dict) -> dict:
        """marshmallow_jsonschema  library add additional properties
        for its generated schemas, but they are useless for my purposes,
        therefore the method clears them"""
        for schema in schemas.values():
            schema.pop('additionalProperties', None)
        return schemas

    def generate_json_schemas(self) -> dict:
        """Generate JSON Schemas using marshmallow_jsonschema
        library. But resulting dict has the next structure:
        {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            'definitions': [schema_one, schema_two, ...],
            '$ref': '#/definitions/SomeSchema',
        }
        because this library supposed to generate one schema, but i
        use it to generate multiple schemas. Therefore, format of
        resulting dict has redundant structure. For my purpose,
        all useful data placed in 'definitions' key"""
        json_schema = CustomJsonSchema()
        resulting_schemas = {}
        for schema in self.defined_marshmallow_schemas:
            resulting_schemas.update(json_schema.dump(schema))
        return resulting_schemas['definitions']

    def set_response_for_openapi_method(
        self, openapi_method: dict, schema=None,
    ):
        if not schema:
            return

        response_schema = dict_set(
            openapi_method, 'responses.200.content.application/json.schema', {},
        )
        if schema.many:
            response_schema['type'] = 'array'
            response_schema['items'] = {
                '$ref': self.SCHEMA_PATH_TEMPLATE.format(schema.json_schema_name),
            }
        else:
            response_schema['$ref'] = self.SCHEMA_PATH_TEMPLATE.format(
                schema.json_schema_name,
            )

    def set_request_for_openapi_method(
        self, openapi_method: dict, schema: CustomSchema = None,
    ):
        if schema and isinstance(schema, CustomSchema):
            request_schema = dict_set(
                openapi_method, 'requestBody.content.application/json.schema',
                {},
            )
            schema_path = self.SCHEMA_PATH_TEMPLATE.format(schema.json_schema_name)
            request_schema['$ref'] = schema_path

    def set_query_params(self, openapi_method: dict, query_params: dict) -> None:
        if not query_params:
            return

        parameters = openapi_method.setdefault('parameters', [])
        for model_obj, fields in query_params.items():
            for field in fields:
                param_type = self.python_type_to_string_map(
                    getattr(model_obj, field).type.python_type
                )
                model_name = get_name_of_model(model_obj)
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
        self, path: str, method: str, request_schema: Schema = None, response_schema: Schema = None, query_params: dict = None,
    ):
        # in the framework /schema/ is used for openapi, therefore no need
        # create openapi description of method that create openapi schema
        if path == '/schema/':
            return

        openapi_new_method = dict_set(
            self.openapi_object,
            f'paths.{path}.{method}',
            {},
        )
        # IMPORTANT. In this brackets can't be comma, with comma
        # operationId will be tuple, but must be string
        openapi_new_method['operationId'] = (
            path.replace('/', '') + '_' + method.lower()
        )

        self.register_marshmallow_schema(response_schema)
        self.set_response_for_openapi_method(openapi_new_method, response_schema)

        self.register_marshmallow_schema(request_schema)
        self.set_request_for_openapi_method(openapi_new_method, request_schema)

        self.set_query_params(openapi_new_method, query_params)