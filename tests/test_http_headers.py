import pytest

from martin_eden.http_utils import HttpHeadersParser, create_response_headers
from tests.conftest import base_http_request, base_http_result_headers


@pytest.fixture
def http_request():
    return base_http_request


@pytest.fixture
def http_request_with_query_params():
    return base_http_request.replace(
        '/users/', '/users/?some_param=some_value',
    )


@pytest.fixture
def http_headers():
    return base_http_result_headers


def test_method_name(http_request):
    parser = HttpHeadersParser(http_request)
    assert parser.method_name == 'GET'


def test_path(http_request):
    parser = HttpHeadersParser(http_request)
    assert parser.path == '/users/'


def test_path_with_query_params(http_request_with_query_params):
    parser = HttpHeadersParser(http_request_with_query_params)
    assert parser.path == '/users/'


def test_empty_query_params(http_request):
    parser = HttpHeadersParser(http_request)
    assert parser.query_params == {}


def test_not_empty_query_params(http_request_with_query_params):
    parser = HttpHeadersParser(http_request_with_query_params)
    assert parser.query_params == {'some_param': 'some_value'}


def test_empty_body(http_request):
    parser = HttpHeadersParser(http_request)
    assert parser.body == ''


def test_not_empty_body(http_request):
    http_request = http_request + '\n{"test: "test"}'
    parser = HttpHeadersParser(http_request)
    assert parser.body == '{"test: "test"}'


@pytest.mark.parametrize('line_break_char', ('\r', '\r\n'))
def test_line_break_detect(http_request, line_break_char):
    parser = HttpHeadersParser(http_request)
    assert parser.line_break_char == '\n'

    parser = HttpHeadersParser(
        http_request.replace('\n', line_break_char),
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
