import dataclasses
import enum
from dataclasses import field, make_dataclass
from datetime import date, datetime
from typing import Callable

from marshmallow.fields import Date, DateTime, Int, Nested, Str
from marshmallow_enum import EnumField as MarshmallowEnum
from sqlalchemy.ext.asyncio import (AsyncAttrs, AsyncEngine,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from core import CustomSchema
from utils import (get_name_of_model, get_python_field_type_from_alchemy_field,
                   is_enum_alchemy_field, is_property_secondary_relation,
                   is_simple_alchemy_field, is_special_alchemy_field)


class Base(AsyncAttrs, DeclarativeBase):
    pass


types_map = {
    str: Str,
    int: Int,
    date: Date,
    datetime: DateTime,
}

inverse_types_map = {
    value: key for key, value in types_map.items()
}


def query_params_to_alchemy_filters(filters, query_param, value):
    """Example of query_param:
        user__first_name__like=martin"""
    model_name, field_name, method_name = query_param.split('__')

    model_class = None
    for model_class_iter in filters.keys():
        if get_name_of_model(model_class_iter) == model_name:
            model_class = model_class_iter
    if not model_class:
        return None

    field_obj = getattr(model_class, field_name)
    method_obj = getattr(field_obj, method_name)
    if method_name == 'like':
        return method_obj(f'%{value}%')
    else:
        return method_obj(value)


class SqlAlchemyToMarshmallow(type(Base)):
    """Metaclass get sql alchemy model, creates marshmallow
    schema based on it"""

    def __new__(cls, name, bases, fields):
        origin_model: Base = bases[0]

        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not all((
                field_name.startswith('_'),
                is_special_alchemy_field(field_name),
                is_property_secondary_relation(origin_model, field_name),
            ))
        ]

        result_fields = {}
        for field_name in origin_model_field_names:
            # add simple fields: int, str, etc.
            if is_simple_alchemy_field(origin_model, field_name):
                python_field_type = get_python_field_type_from_alchemy_field(
                    origin_model, field_name,
                )

                if is_enum_alchemy_field(origin_model, field_name):
                    result_fields[field_name] = MarshmallowEnum(
                        python_field_type, required=False,
                    )
                else:
                    result_fields[field_name] = (
                        types_map[python_field_type](required=False)
                    )
            else:
                # add nested fields
                if fields.get(field_name):
                    result_fields[field_name] = Nested(
                        fields[field_name], required=False,
                    )

        result_model = CustomSchema.from_dict(result_fields, name=name)
        return result_model


class MarshmallowToDataclass(type(CustomSchema)):
    def __new__(cls, name, bases, fields):
        origin_schema_class = bases[0]
        origin_schema = origin_schema_class()
        origin_model_fields = origin_schema.fields

        # Create simple fields, of type int, str, etc.
        result_fields = [
            (field_name, inverse_types_map[type(field_type)], field(default=None))
            for field_name, field_type in origin_model_fields.items()
            if not isinstance(field_type, Nested)
            and not hasattr(field_type, 'enum')
        ]

        # for enums
        result_fields.extend([
            (field_name, field_type.enum, field(default=None))
            for field_name, field_type in origin_model_fields.items()
            if not isinstance(field_type, Nested)
            and hasattr(field_type, 'enum')
        ])

        # Create complex fields, of marshmallow schemas,
        # for creating nested marshmallow schemas
        for field_name, field_type in origin_model_fields.items():
            if isinstance(field_type, Nested):
                result_fields.append(
                    (field_name, fields['__annotations__'][field_name], field(default=None))
                )

        @dataclasses.dataclass
        class BaseDataclass:
            pass

        result_model = make_dataclass(name, fields=result_fields, bases=(BaseDataclass,))
        return result_model


class DataBase:
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine(
            'postgresql+asyncpg://alexander.bezgin:123@localhost/framework',
            echo=True,
        )
        self.create_session: Callable = async_sessionmaker(self.engine)
