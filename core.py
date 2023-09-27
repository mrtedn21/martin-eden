from marshmallow import Schema


class CustomSchema(Schema):
    def __init__(self, *args, json_schema_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_schema_name = json_schema_name
