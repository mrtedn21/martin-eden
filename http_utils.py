# Example of http headers for convenience:
# GET /some/path HTTP/1.1
# Host: localhost:8001
# Connection: keep-alive
from typing import Optional


class HttpMethod:
    OPTIONS = 'OPTIONS'
    POST = 'POST'
    GET = 'GET'


class HttpHeadersParser:
    def __init__(self, message: str):
        self.message: str = message
        self._detect_line_break_char()
        self.lines_of_header: list[str] = message.split(self.line_break_char)

        self.method_name: str = self._get_method_name()
        self.path: str = self._get_path()
        self.query_params: Optional[str] = self._get_query_params()
        self.body: str = self._get_body()

    def _detect_line_break_char(self):
        self.line_break_char: str = '\r'

        if '\r\n' in self.message:
            self.line_break_char = '\r\n'
        elif '\n' in self.message:
            self.line_break_char = '\n'

    def _get_method_name(self) -> str:
        """Method name is first word of first line"""
        first_line = self.lines_of_header[0]
        first_word = first_line.split(' ')[0]
        return first_word

    def _get_path_and_query_params(self):
        first_line = self.lines_of_header[0]
        second_word = first_line.split(' ')[1]
        return second_word.split('?')

    def _get_path(self):
        """Path is second name in first line"""
        url_parts = self._get_path_and_query_params()
        return url_parts[0]

    def _get_query_params(self):
        url_parts = self._get_path_and_query_params()
        if len(url_parts) == 1:
            return

        query_params = {}
        for query_param in url_parts[1].split('&'):
            key, value = query_param.split('=')
            query_params[key] = value
        return query_params

    def _get_body(self):
        """Body of http message starts after two line break characters"""
        position_of_body_starts = (
            self.message.find(self.line_break_char * 2) +
            len(self.line_break_char * 2)
        )
        return self.message[position_of_body_starts:]


def create_response_headers(
    status: int, content_type: Optional[str] = None, for_options: bool = False,
) -> str:
    """Status is number, 200 or 404
    content_type examples is:
    * application/json
    * text/html.
    """
    allow_methods = 'Allow: OPTIONS, GET, POST\n'
    if content_type:
        content_type = f'Content-Type: {content_type};charset=UTF-8\n'

    return (
        f'HTTP/1.0 {status}\n'
        'Access-Control-Allow-Origin: *\n'
        'Access-Control-Allow-Methods: POST, GET, OPTIONS\n'
        'Access-Control-Allow-Headers: origin, content-type, accept\n'
        'Access-Control-Allow-Credentials: true\n'
        'Access-Control-Max-Age: 86400\n'
        f'{allow_methods if for_options else ""}'
        f'{content_type if content_type else ""}'
        f'\n'
    )
