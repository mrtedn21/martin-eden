import dataclasses
from dataclasses import field, make_dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable
from martin_eden.settings import Settings

from marshmallow.fields import Date, DateTime, Int, Nested, Str
from marshmallow_enum import EnumField as MarshmallowEnum
from sqlalchemy.ext.asyncio import (AsyncAttrs, AsyncEngine,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from martin_eden.base import CustomSchema
from martin_eden.utils import (get_name_of_model,
                               get_python_field_type_from_alchemy_field,
                               is_enum_alchemy_field,
                               is_property_secondary_relation,
                               is_simple_alchemy_field,
                               is_special_alchemy_field)


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


def query_params_to_alchemy_filters(
    filters: dict, query_param: str, value: str,
) -> Any:
    """Example of query_param argument from url:
       * user__first_name__like=martin
       * user__age__in=20,21,22
       * user__age__exactly=25"""
    model_name, field_name, method_name = query_param.split('__')

    model_class = None
    for model_class_iter in filters:
        if get_name_of_model(model_class_iter) == model_name:
            model_class = model_class_iter
    if not model_class:
        return None

    field_obj = getattr(model_class, field_name)
    if method_name == 'like':
        method_obj = getattr(field_obj, method_name)
        return method_obj(f'%{value}%')
    elif method_name == 'exactly':
        method_obj = getattr(field_obj, 'in_')
        return method_obj([int(value)])
    elif method_name == 'in':
        method_obj = getattr(field_obj, 'in_')
        return method_obj(list(map(int, value.split(','))))


class SqlAlchemyToMarshmallow(type(Base)):
    """Metaclass get sql alchemy model, creates marshmallow
    schema based on it"""

    def __new__(cls, name: str, bases: Iterable, fields: dict) -> type:
        origin_model: Base = bases[0]

        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not any((
                field_name.startswith('_'),
                is_special_alchemy_field(field_name),
                is_property_secondary_relation(origin_model, field_name),
            ))
        ]

        result_fields = {}
        for field_name in origin_model_field_names:
            # add simple fields: int, str, date, datetime, etc.
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
            # add nested fields
            elif fields.get(field_name):
                result_fields[field_name] = Nested(
                    fields[field_name], required=False,
                )

        result_model = CustomSchema.from_dict(result_fields, name=name)
        return result_model


@dataclasses.dataclass
class BaseDataclass:
    pass


class MarshmallowToDataclass(type(CustomSchema)):
    def __new__(cls, name: str, bases: Iterable, fields: dict) -> type:
        origin_schema_class = bases[0]
        origin_schema = origin_schema_class()
        origin_model_fields = origin_schema.fields

        result_fields = []
        for field_name, field_type in origin_model_fields.items():
            if isinstance(field_type, Nested):
                new_type_for_dataclass = (
                    fields['__annotations__'][field_name]
                )
            elif hasattr(field_type, 'enum'):
                new_type_for_dataclass = field_type.enum
            else:
                new_type_for_dataclass = (
                    inverse_types_map[type(field_type)]
                )

            result_fields.append((
                field_name, new_type_for_dataclass, field(default=None),
            ))

        result_dataclass = make_dataclass(
            name, fields=result_fields, bases=(BaseDataclass,),
        )
        return result_dataclass


class DataBase:
    def __init__(self) -> None:
        settings = Settings()
        self.engine: AsyncEngine = create_async_engine(
            settings.postgres_url,
            echo=True,
        )
        self.create_session: Callable = async_sessionmaker(self.engine)
