import os


def read_env(var_name, default=None):
    if default is None:
        return os.environ[var_name]
    else:
        return os.environ.get(var_name, default=default)


def read_int(var_name, default=None):
    return int(read_env(var_name, default=default))


def read_str(var_name, default=None):
    return read_env(var_name, default=default)


class Settings:
    server_host = read_str('SERVER_HOST')
    server_port = read_int('SERVER_PORT')
    postgres_url = read_str('POSTGRES_URL')
    log_level = read_str('LOG_LEVEL')
