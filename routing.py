from typing import Callable, Iterable

DictOfRoutes = dict[str, dict[str, Callable]]

routes: DictOfRoutes = {}


def _register_route(
    path: str, methods: Iterable[str], controller: Callable
) -> None:
    new_path = routes.setdefault(path, {})
    for method in methods:
        new_path[method.upper()] = controller


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
