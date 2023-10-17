from typing import Callable, Iterable
from core import Controller

from openapi import add_openapi_path
from marshmallow import Schema

DictOfRoutes = dict[str, dict[str, Callable]]

routes: DictOfRoutes = {}


def _register_route(
    path: str,
    methods: Iterable[str],
    controller: Callable,
    request_schema: Schema = None,
    response_schema: Schema = None,
    query_params: dict = None,
) -> None:
    new_path = routes.setdefault(path, {})
    for method in methods:
        new_path[method.upper()] = controller
        add_openapi_path(path, method, request_schema, response_schema, query_params)


def get_controller(path: str, method: str) -> Controller:
    methods = routes[path]
    controller = methods[method.upper()]
    return controller


def register_route(path, methods, request_schema=None, response_schema=None, query_params=None):
    """This is decorator only, wrapping over _register_route."""
    def wrap(func):
        def wrapped_f(*args, **kwargs):
            func(*args, **kwargs)

        func.request_schema = request_schema
        func.response_schema = response_schema
        func.query_params = query_params
        _register_route(path, methods, func, request_schema, response_schema, query_params)
        return wrapped_f

    return wrap
