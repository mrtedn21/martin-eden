import inspect
from typing import Callable


def get_name_of_model(model_class):
    model_name = model_class.__name__
    # remove "Orm" postfix from model name
    model_name = model_name[:-3]
    model_name = model_name.lower()
    return model_name


def get_argument_names(foo: Callable) -> tuple[str]:
    return tuple(dict(inspect.signature(foo).parameters).keys())
