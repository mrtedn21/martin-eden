import enum
import inspect
from typing import Callable


def get_name_of_model(model_class):
    model_name = model_class.__name__
    # remove "Orm" postfix from model name
    model_name = model_name[:-3]
    model_name = model_name.lower()
    return model_name


def get_argument_names(foo: Callable) -> tuple[str]:
    """Function return argument names of foo"""
    return tuple(dict(inspect.signature(foo).parameters).keys())


def is_special_alchemy_field(field_name: str) -> bool:
    """Function determines iF field_name is special sql alchemy field"""
    alchemy_fields = ('registry', 'metadata', 'awaitable_attrs')
    return field_name in alchemy_fields


def is_simple_alchemy_field(alchemy_model, field_name: str) -> bool:
    """Function determine if field_name is simple alchemy field.
    Simple field means str, int, etc

    If sqlalchemy if model's field has attribute "type" it means
    that field is simple"""
    return hasattr(getattr(alchemy_model, field_name), 'type')


def is_enum_alchemy_field(alchemy_model, field_name: str) -> bool:
    """Function determine if field of alchemy_model is enum"""
    field_type = getattr(alchemy_model, field_name).type.python_type
    return issubclass(field_type, enum.Enum)


def get_python_field_type_from_alchemy_field(alchemy_model, field_name: str):
    return getattr(alchemy_model, field_name).type.python_type


def is_property_secondary_relation(model, attribute_name):
    """Sqlalchemy in its models force declare one relation in two models.
    What means. For example will take model "order" and model "product".
    Every "order" may have one "product". In database, in sql when we create
    table "product", we don't write that it relates to "order", only in table
    "order" we create product_id and create foreign key, that references
    to "product" table. In this case reference from "order" to "product"
    is primary relation. Nevertheless, one "product" can reference to
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
