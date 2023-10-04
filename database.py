import enum
from sqlalchemy import Table, Column
import dataclasses
from datetime import date, datetime
from typing import Callable
from dataclasses import make_dataclass, field
from core import CustomSchema

from marshmallow.fields import Str, Date, Int, Nested, DateTime
from marshmallow_enum import EnumField as MarshmallowEnum

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
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


registered_models = {}


def register_model(model_class):
    model_name = model_class.__name__
    # remove "Orm" postfix from model name
    model_name = model_name[:-3]
    model_name = model_name.lower()
    registered_models[model_name] = model_class


def query_params_to_alchemy_filters(query_param, value):
    """Example of query_param:
        user__first_name__like=martin"""
    model_name, field_name, method_name = query_param.split('__')
    model_class = registered_models[model_name]
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
        register_model(origin_model)

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


class UserOrm(Base):
    __tablename__ = 'users'

    pk: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[date]
    messages: Mapped['MessageOrm'] = relationship(back_populates='created_by')

    city_id: Mapped[int] = mapped_column(
        ForeignKey('cities.pk'), nullable=True,
    )
    city: Mapped['CityOrm'] = relationship(back_populates='city_users')

    language_id: Mapped[int] = mapped_column(
        ForeignKey('languages.pk'), nullable=True,
    )
    language: Mapped['LanguageOrm'] = relationship(back_populates='language_users')

    gender_id: Mapped[int] = mapped_column(
        ForeignKey('genders.pk'), nullable=True,
    )
    gender: Mapped['GenderOrm'] = relationship(back_populates='gender_users')


class CityOrm(Base):
    __tablename__ = 'cities'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.pk'))
    country: Mapped['CountryOrm'] = relationship(back_populates='cities')
    city_users: Mapped[list['UserOrm']] = relationship(back_populates='city')


class CountryOrm(Base):
    __tablename__ = 'countries'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    cities: Mapped[list['CityOrm']] = relationship(back_populates='country')


class LanguageOrm(Base):
    __tablename__ = 'languages'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    language_users: Mapped[list['UserOrm']] = relationship(back_populates='language')


class GenderOrm(Base):
    __tablename__ = 'genders'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    gender_users: Mapped[list['UserOrm']] = relationship(back_populates='gender')


class ChatType(enum.Enum):
    DIRECT = 'direct'
    GROUP = 'group'
    SELF = 'self'


class ChatOrm(Base):
    __tablename__ = 'chats'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True)
    chat_type: Mapped[ChatType] = mapped_column(default=ChatType.DIRECT)

    last_message_id: Mapped[int] = mapped_column(ForeignKey('users.pk'), nullable=True)
    last_message: Mapped['MessageOrm'] = relationship(back_populates='last_message_in_chat')
    messages: Mapped[list['MessageOrm']] = relationship(back_populates='chat')

    participants: Mapped[list[UserOrm]] = relationship(secondary=Table(
        "chats_to_users",
        Base.metadata,
        Column("chat_id", ForeignKey("chats.pk")),
        Column("user_id", ForeignKey("users.pk")),
    ))


class MessageOrm(Base):
    __tablename__ = 'messages'

    pk: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    date_time: Mapped[datetime] = mapped_column(default=datetime.now)

    created_by_id: Mapped[int] = mapped_column(ForeignKey('users.pk'))
    created_by: Mapped['UserOrm'] = relationship(back_populates='messages')

    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.pk'))
    chat: Mapped['ChatOrm'] = relationship(back_populates='messages')
    last_message_in_chat: Mapped['ChatOrm'] = relationship(back_populates='last_message')

    reply_to_message_id: Mapped[int] = mapped_column(ForeignKey('messages.pk'), nullable=True)
    reply_to_message: Mapped['MessageOrm'] = relationship(remote_side=[pk])


class DataBase:
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine(
            'postgresql+asyncpg://alexander.bezgin:123@localhost/framework',
            echo=True,
        )
        self.create_session: Callable = async_sessionmaker(self.engine)
