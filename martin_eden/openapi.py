import json
from pathlib import Path
from typing import TYPE_CHECKING

from martin_eden.base import CustomJsonSchema, CustomSchema
from martin_eden.utils import (
    dict_set,
    get_name_of_model,
    get_operation_id_for_openapi,
    get_python_field_type_from_alchemy_field,
)

if TYPE_CHECKING:
    from database import Base as BaseModel


# This dict needs to detect type of query param by filter name
map_filter_name_to_type = {
    'in': 'string',
    'like': 'string',
    'exactly': 'int',
}


class OpenApiBuilder:
    _instance = None
    SCHEMA_PATH_TEMPLATE = '#/components/schemas/{}'

    def __new__(cls) -> 'OpenApiBuilder':
        """This method makes from OpenApiBuilder - singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.defined_marshmallow_schemas = set()
            with open(Path(__file__).parent / 'example.json') as file:
                cls.openapi_object = json.load(file)
        return cls._instance

    def register_marshmallow_schema(self, schema: CustomSchema) -> None:
        """Register schemas for openapi doc - using concrete
        instance of marshmallow schema. Not class of marshmallow
        schema, but instance, because it is more flexible"""
        self.defined_marshmallow_schemas.add(schema)

    def change_definitions_references(self, dct: dict) -> None:
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

    def write_marshmallow_schemas_to_openapi_doc(self) -> None:
        """The method writes all registered schemas to openapi documentation"""
        if not self.defined_marshmallow_schemas:
            return

        marshmallow_json_schemas = self.generate_json_schemas()
        self.change_definitions_references(marshmallow_json_schemas)
        result_json_schemas = self.clean_schemas_from_additional_properties(
            marshmallow_json_schemas,
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
        self, openapi_method: dict, schema: CustomSchema,
    ) -> None:
        response_schema = dict_set(
            openapi_method,
            'responses.200.content.application/json.schema',
            {},
        )
        if schema.many:
            response_schema['type'] = 'array'
            response_schema['items'] = {
                '$ref': self.SCHEMA_PATH_TEMPLATE.format(
                    schema.json_schema_name,
                ),
            }
        else:
            response_schema['$ref'] = self.SCHEMA_PATH_TEMPLATE.format(
                schema.json_schema_name,
            )

    def set_request_for_openapi_method(
        self, openapi_method: dict, schema: CustomSchema,
    ) -> None:
        if isinstance(schema, CustomSchema):
            request_schema = dict_set(
                openapi_method, 'requestBody.content.application/json.schema',
                {},
            )
            schema_path = self.SCHEMA_PATH_TEMPLATE.format(
                schema.json_schema_name,
            )
            request_schema['$ref'] = schema_path

    def set_query_params(
        self, openapi_method: dict, query_params: dict,
    ) -> None:
        parameters = openapi_method.setdefault('parameters', [])
        for model_class, fields in query_params.items():
            for field_name in fields:
                parameters.extend(
                    self.generate_query_param_for_openapi(
                        model_class, field_name,
                    ),
                )

    def generate_query_param_for_openapi(
        self, model_class: 'BaseModel', field_name: str,
    ) -> dict:
        model_name = get_name_of_model(model_class)
        python_field_type = get_python_field_type_from_alchemy_field(
            model_class, field_name,
        )
        filter_names = self.get_filter_names_for_param_type(
            python_field_type,
        )
        return [{
            'name': f'{model_name}__{field_name}__{filter_name}',
            'in': 'query',
            'schema': {'type': map_filter_name_to_type[filter_name]},
        } for filter_name in filter_names]

    @staticmethod
    def get_filter_names_for_param_type(param_type) -> list[str]:
        return ['like'] if param_type is str else ['in', 'exactly']

    def add_openapi_path(
        self,
        path: str,
        method: str,
        request_schema: CustomSchema = None,
        response_schema: CustomSchema = None,
        query_params: dict = None,
    ) -> None:
        # in the framework /schema/ is used for openapi, therefore no need
        # create openapi description of method that create openapi schema
        if path == '/schema/':
            return

        openapi_new_method = dict_set(
            self.openapi_object, f'paths.{path}.{method}', {},
        )
        openapi_new_method['operationId'] = (
            get_operation_id_for_openapi(path, method)
        )

        if response_schema:
            self.register_marshmallow_schema(response_schema)
            self.set_response_for_openapi_method(
                openapi_new_method, response_schema,
            )

        if request_schema:
            self.register_marshmallow_schema(request_schema)
            self.set_request_for_openapi_method(
                openapi_new_method, request_schema,
            )

        if query_params:
            self.set_query_params(openapi_new_method, query_params)
