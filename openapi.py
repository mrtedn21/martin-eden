import json

with open('example.json', 'r') as file:
    openapi_object = json.load(file)


def add_schema(name: str, model):
    openapi_object['components']['schemas'][name] = model.model_json_schema()

