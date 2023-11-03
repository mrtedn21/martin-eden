from martin_eden.http_utils import (
    HttpHeadersParser, create_response_headers,
)
import pytest


base_http_message = (
    'GET /users/ HTTP/1.1\n'
    'Host: localhost:8001\n'
    'Connection: keep-alive\n'
    'sec-ch-ua: "Chromium";v="118", "Google Chrome";v="118", '
    '"Not=A?Brand";v="99"\n'
    'sec-ch-ua-mobile: ?0\n'
    'sec-ch-ua-platform: "macOS"\n'
    'Upgrade-Insecure-Requests: 1\n'
    'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 '
    'Safari/537.36\n'
    'Accept: text/html,application/xhtml+xml,application/xml;'
    'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
    'application/signed-exchange;v=b3;q=0.7\n'
    'Sec-Fetch-Site: none\n'
    'Sec-Fetch-Mode: navigate\n'
    'Sec-Fetch-User: ?1\n'
    'Sec-Fetch-Dest: document\n'
    'Accept-Encoding: gzip, deflate, br\n'
    'Accept-Language: en-US,en;q=0.9,ru;q=0.8,ru-RU;q=0.7\n'
    'Cookie: token=a0966813f9b27b2a545c75966fd87815660787a3; '
    'person_pk=1; csrftoken=3fQjKaaBDsfYyAERtNK9rZpY2gX2yQWl; '
    'session=bc8145dc-7e09-46f5-b5fa-789863559f3a.'
    'EetDaRq0uVnaC8vMKj2YhEYL5Fs\n'
)


@pytest.fixture
def http_message():
    return base_http_message


@pytest.fixture
def http_message_with_query_params():
    return base_http_message.replace(
        '/users/', '/users?some_param=some_value',
    )


@pytest.fixture
def http_headers():
    return (
        'HTTP/1.0 200\n'
        'Access-Control-Allow-Origin: *\n'
        'Access-Control-Allow-Methods: POST, GET, OPTIONS\n'
        'Access-Control-Allow-Headers: origin, content-type, accept\n'
        'Access-Control-Allow-Credentials: true\n'
        'Access-Control-Max-Age: 86400\n\n'
    )


def test_method_name(http_message):
    parser = HttpHeadersParser(http_message)
    assert parser.method_name == 'GET'


def test_path(http_message):
    parser = HttpHeadersParser(http_message)
    assert parser.path == '/users/'


def test_path_with_query_params(http_message_with_query_params):
    parser = HttpHeadersParser(http_message_with_query_params)
    assert parser.path == '/users'


def test_empty_query_params(http_message):
    parser = HttpHeadersParser(http_message)
    assert parser.query_params == {}


def test_not_empty_query_params(http_message_with_query_params):
    parser = HttpHeadersParser(http_message_with_query_params)
    assert parser.query_params == {'some_param': 'some_value'}


def test_empty_body(http_message):
    parser = HttpHeadersParser(http_message)
    assert parser.body == ''


def test_not_empty_body(http_message):
    http_message = http_message + '\n{"test: "test"}'
    parser = HttpHeadersParser(http_message)
    assert parser.body == '{"test: "test"}'


@pytest.mark.parametrize('line_break_char', ('\r', '\r\n'))
def test_line_break_detect(http_message, line_break_char):
    parser = HttpHeadersParser(http_message)
    assert parser.line_break_char == '\n'

    parser = HttpHeadersParser(
        http_message.replace('\n', line_break_char),
    )
    assert parser.line_break_char == line_break_char


def test_headers_creating(http_headers):
    headers = create_response_headers(200)
    assert headers == http_headers


def test_headers_creating_for_options(http_headers):
    http_headers = (
        http_headers[:-1] +
        'Allow: OPTIONS, GET, POST\n\n'
    )
    headers = create_response_headers(200, for_options=True)
    assert headers == http_headers


def test_headers_creating_with_content_type(http_headers):
    http_headers = (
        http_headers[:-1] +
        'Content-Type: application/json;charset=UTF-8\n\n'
    )
    headers = create_response_headers(200, 'application/json')
    assert headers == http_headers
