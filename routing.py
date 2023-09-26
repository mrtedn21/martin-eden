from typing import Callable, Iterable

from openapi import add_openapi_path
from marshmallow import Schema

DictOfRoutes = dict[str, dict[str, Callable]]

routes: DictOfRoutes = {}


def _register_route(
    path: str,
    methods: Iterable[str],
    controller: Callable,
    request: Schema = None,
    response: Schema = None,
) -> None:
    new_path = routes.setdefault(path, {})
    for method in methods:
        new_path[method.upper()] = controller
        add_openapi_path(path, method, controller, request, response)


def get_controller(path: str, method: str):
    methods = routes[path]
    controller = methods[method.upper()]
    return controller


def register_route(path, methods, request=None, response=None):
    """This is decorator only, wrapping over _register_route."""
    def wrap(func):
        def wrapped_f(*args, **kwargs):
            func(*args, **kwargs)

        func.request = request
        func.response = response
        _register_route(path, methods, func, request, response)
        return wrapped_f

    return wrap
