# Example of http headers for convenience:
# GET /some/path HTTP/1.1
# Host: localhost:8001
# Connection: keep-alive


class HttpHeadersParser:
    def __init__(self, message: str):
        self.message: str = message
        self._detect_line_break_char()
        self.lines_of_header: list[str] = message.split(
            self.line_break_char
        )

    def _detect_line_break_char(self):
        self.line_break_char: str = '\r'

        if '\r\n' in self.message:
            self.line_break_char = '\r\n'
        elif '\n' in self.message:
            self.line_break_char = '\n'

    def get_method_name(self) -> str:
        # Method name is first word of first line
        first_line = self.lines_of_header[0]
        first_word = first_line.split(' ')[0]
        return first_word

    def get_path(self):
        # Path is second word of first line
        first_line = self.lines_of_header[0]
        second_word = first_line.split(' ')[1]
        return second_word

    def get_body(self):
        position_of_body_starts = (
            self.message.find(self.line_break_char * 2) +
            len(self.line_break_char * 2)
        )
        return self.message[position_of_body_starts:]


def create_response_headers(status: int, content_type: str):
    """
    status is number, 200 or 404
    content_type examples is:
    * application/json
    * text/html
    """
    return (
        f'HTTP/1.0 {status}\n'
        f'Access-Control-Allow-Origin: *\n'
        f'Content-Type: {content_type};charset=UTF-8\n\n'
    )
