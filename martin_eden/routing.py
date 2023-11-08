from typing import Callable, ParamSpecArgs, ParamSpecKwargs

from martin_eden.base import Controller, CustomSchema
from martin_eden.openapi import OpenApiBuilder

DictOfRoutes = dict[str, dict[str, Controller]]

routes: DictOfRoutes = {}


class ControllerDefinitionError(Exception):
    pass


class FindControllerError(Exception):
    pass


def _register_route(
    path: str,
    method: str,
    controller: Controller,
    request_schema: CustomSchema = None,
    response_schema: CustomSchema = None,
    query_params: dict = None,
) -> None:
    new_path = routes.setdefault(path, {})
    new_path[method.upper()] = controller
    OpenApiBuilder().add_openapi_path(
        path, method, request_schema, response_schema, query_params,
    )


def get_controller(path: str, method: str) -> Controller:
    try:
        methods = routes[path]
        controller = methods[method.upper()]
    except KeyError as exc:
        # Temp decision for not existing paths
        # In future must return 404 not found
        raise FindControllerError(
            f'Controller not found with path: {path} and method: {method}',
        ) from exc
    return controller


def register_route(
    path: str,
    method: str,
    request_schema: CustomSchema = None,
    response_schema: CustomSchema = None,
    query_params: dict = None,
) -> Callable:
    """This is decorator only, wrapping over _register_route."""
    def wrap(func: Callable) -> Callable:
        def wrapped_f(*args: ParamSpecArgs, **kwargs: ParamSpecKwargs) -> None:
            func(*args, **kwargs)

        func.request_schema = request_schema
        func.response_schema = response_schema
        func.query_params = query_params
        _register_route(
            path, method, func, request_schema, response_schema, query_params,
        )
        return wrapped_f

    return wrap
