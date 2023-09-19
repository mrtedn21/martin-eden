from datetime import date
from typing import Callable

from pydantic import ConfigDict, create_model
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    InstrumentedAttribute,
    Mapped,
    mapped_column,
    relationship,
)

from openapi import register_pydantic_model


class Base(AsyncAttrs, DeclarativeBase):
    pass


class SqlAlchemyToPydantic(type(Base)):
    """Metaclass that get sql alchemy model fields, creates pydantic
    model based on them and moreover, metaclass extends schemas of
    openapi object with models it creates.

    Example:
    -------
    class NewModel(SomeSqlAlchemyModel, metaclass=SqlAlchemyToPydantic):
        fields = '__all__'

    fields attribute can be on of:

    * '__all__' - means that pydantic model will be with all
        fields of alchemy model
    * '__without_pk__' - means will be all fields instead of pk
    * tuple[str] - is tuple of fields that will be used
    """

    def __new__(cls, name, bases, fields):
        origin_model = bases[0]

        # alchemy_fields variable needs to exclude these
        # properties from origin_model_field_names
        alchemy_fields = ('registry', 'metadata', 'awaitable_attrs')
        # In addition, I filter from secondary relations, because it is
        # harmful in future pydantic model
        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not field_name.startswith('_')
            and field_name not in alchemy_fields
            and not cls.is_property_secondary_relation(origin_model, field_name)
            and not cls.is_property_foreign_key(origin_model, field_name)
        ]

        defined_fields = fields['fields']
        if defined_fields == '__all__':
            defined_fields = origin_model_field_names
        elif defined_fields == '__without_pk__':
            defined_fields = tuple(set(origin_model_field_names) - {'pk'})

        # Create simple fields, of type int, str, etc.
        result_fields = {
            field_name: (
                getattr(origin_model, field_name).type.python_type, ...
            )
            for field_name in defined_fields
            if field_name in origin_model_field_names and
            # if alchemy field has 'type' property,
            # it means the field is simple, int, str, etc.
            hasattr(getattr(origin_model, field_name), 'type')
        }

        # Create complex fields, of pydantic models,
        # for creating nested pydantic models
        result_fields.update({
            field_name: (fields[field_name], ...)
            for field_name in defined_fields
            if field_name in origin_model_field_names
            and fields.get(field_name)
            # if alchemy field hasn't 'type' property, it means the field is relation
            and not hasattr(getattr(origin_model, field_name), 'type')
        })

        result_model = create_model(
            name,
            **result_fields,
            __config__=ConfigDict(from_attributes=True),
        )
        register_pydantic_model(name, result_model)
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


class UserOrm(Base):
    __tablename__ = 'users'

    pk: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[date]

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


class DataBase:
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine(
            'postgresql+asyncpg://alexander.bezgin:123@localhost/framework',
            echo=True,
        )
        self.create_session: Callable = async_sessionmaker(self.engine)
