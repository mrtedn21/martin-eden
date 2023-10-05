import enum
from utils import get_string_of_model
import dataclasses
from datetime import date, datetime
from typing import Callable
from dataclasses import make_dataclass, field
from core import CustomSchema

from marshmallow.fields import Str, Date, Int, Nested, DateTime
from marshmallow_enum import EnumField as MarshmallowEnum

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


types_map = {
    str: Str,
    int: Int,
    date: Date,
    datetime: DateTime,
}

reverse_types_map = {
    value: key for key, value in types_map.items()
}


def query_params_to_alchemy_filters(filters, query_param, value):
    """Example of query_param:
        user__first_name__like=martin"""
    model_name, field_name, method_name = query_param.split('__')

    model_class = None
    for model_class_iter in filters.keys():
        if get_string_of_model(model_class_iter) == model_name:
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
    """Metaclass that get sql alchemy model fields, creates marshmallow
    schemas based on them and moreover, metaclass extends schemas of
    openapi object with models it creates.

    Example:
    -------
    class NewModel(SomeSqlAlchemyModel, metaclass=SqlAlchemyToPydantic):
        fields = '__all__'

    fields attribute can be on of:

    * '__all__' - means that marshmallow schema will be with all
        fields of alchemy model
    * '__without_pk__' - means will be all fields instead of pk
    * tuple[str] - is tuple of fields that will be used
    """

    def __new__(cls, name, bases, fields):
        origin_model = bases[0]
        #register_model(origin_model)

        # alchemy_fields variable needs to exclude these
        # properties from origin_model_field_names
        alchemy_fields = ('registry', 'metadata', 'awaitable_attrs')
        # In addition, I filter from secondary relations, because it is
        # harmful in future marshmallow schemas
        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not field_name.startswith('_')
            and field_name not in alchemy_fields
            and not cls.is_property_secondary_relation(origin_model, field_name)
            #and not cls.is_property_foreign_key(origin_model, field_name)
        ]

        # Create simple fields, of type int, str, etc.
        result_fields = {
            field_name: types_map[getattr(origin_model, field_name).type.python_type](required=False)
            for field_name in origin_model_field_names
            # if alchemy field has 'type' property,
            # it means the field is simple, int, str, etc.
            if hasattr(getattr(origin_model, field_name), 'type')
            if not issubclass(getattr(origin_model, field_name).type.python_type, enum.Enum)
        }

        # For enums
        result_fields.update({
            field_name: MarshmallowEnum(getattr(origin_model, field_name).type.python_type, required=False)
            for field_name in origin_model_field_names
            # if alchemy field has 'type' property,
            # it means the field is simple, int, str, etc.
            if hasattr(getattr(origin_model, field_name), 'type')
            if issubclass(getattr(origin_model, field_name).type.python_type, enum.Enum)
        })

        # Create complex fields, of marshmallow schemas,
        # for creating nested marshmallow schemas
        for field_name in origin_model_field_names:
            if (field_name in origin_model_field_names
                and fields.get(field_name)
                and not hasattr(getattr(origin_model, field_name), 'type')
            ):
                result_fields[field_name] = Nested(fields[field_name], required=False)

        result_model = CustomSchema.from_dict(result_fields, name=name)
        return result_model

    @staticmethod
    def is_property_secondary_relation(model, attribute_name):
        """Sqlalchemy in its models force define one relation in two models.
        What means. For example will take model order and model product.
        Every order may have one product. In database, in sql when we create
        table product, we don't write that it relates to order, only in table
        order we create product_id and create foreign key, that references
        to product table. In this case reference from order to product
        is primary relation. Nevertheless, one product can reference to
        multiple orders, but it is not marked in database schema,
        therefore I say that it is secondary relation

        And this function separate primary relation in model from secondary.
        The function return True only if attribute from attribute_name
        argument is secondary relationship."""
        attribute = getattr(model, attribute_name)

        try:
            collection_class = attribute.prop.collection_class
        except AttributeError:
            return False

        if collection_class is not None:
            return True
        else:
            return False

    @staticmethod
    def is_property_foreign_key(model, attribute_name):
        attribute = getattr(model, attribute_name)
        try:
            foreign_keys = attribute.foreign_keys
        except AttributeError:
            return False

        if foreign_keys:
            return True
        else:
            return False


class MarshmallowToDataclass(type(CustomSchema)):
    def __new__(cls, name, bases, fields):
        origin_schema_class = bases[0]
        origin_schema = origin_schema_class()
        origin_model_fields = origin_schema.fields

        # Create simple fields, of type int, str, etc.
        result_fields = [
            (field_name, reverse_types_map[type(field_type)], field(default=None))
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
