from martin_eden.http_utils import HttpHeadersParser
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
