from typing import Callable, Iterable
from openapi import openapi_object
from pydantic import BaseModel

DictOfRoutes = dict[str, dict[str, Callable]]

routes: DictOfRoutes = {}


def _register_route(
    path: str, methods: Iterable[str], controller: Callable,
) -> None:
    new_path = routes.setdefault(path, {})
    openapi_paths = openapi_object.setdefault('paths', {})
    openapi_new_path = openapi_paths.setdefault(path, {})

    for method in methods:
        new_path[method.upper()] = controller
        openapi_new_method = openapi_new_path.setdefault(method, {})
        openapi_new_method['operationId'] = (
            path.replace('/', '') + '_' + method.lower()
        )
        openapi_responses = openapi_new_method.setdefault('responses', {})
        openapi_model_schema = (
            openapi_responses
            .setdefault('200', {})
            .setdefault('content', {})
            .setdefault('application/json', {})
            .setdefault('schema', {})
        )

        for arg, arg_type in controller.__annotations__.items():
            if issubclass(arg_type, BaseModel):
                openapi_model_schema['$ref'] = (
                    f'#/components/schemas/{arg_type.__name__}'
                )




def get_controller(path: str, method: str):
    methods = routes[path]
    controller = methods[method.upper()]
    return controller


def register_route(path, methods):
    """This is decorator only, wrapping over _register_route"""

    def wrap(func):
        def wrapped_f(*args, **kwargs):
            func(*args, **kwargs)
        _register_route(path, methods, func)
        return wrapped_f
    return wrap
