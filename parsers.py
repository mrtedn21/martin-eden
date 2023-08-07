# Example of http headers for convenience:
# GET /some/path HTTP/1.1
# Host: localhost:8001
# Connection: keep-alive


class HttpHeadersParser:
    def __init__(self, message: str):
        self.message: str = message
        self.lines_of_header: list[str] = message.split('\n')

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
