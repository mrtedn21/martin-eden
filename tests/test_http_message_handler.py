import pytest
from martin_eden.routing import ControllerDefinitionError, get_controller, register_route
import json
from martin_eden.openapi import OpenApiBuilder
import asyncio
from martin_eden.core import HttpMessageHandler

pytest_plugins = ('pytest_asyncio',)


@register_route('/test/', 'get')
async def get_openapi_schema() -> str:
    return 'test'


@pytest.fixture
def http_get_request():
    return (
        b'GET /users/ HTTP/1.1\n'
        b'Accept: text/html,application/xhtml+xml, '
        b'application/xml;q=0.9,image/avif,image/webp, '
        b'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\n'
        b'Accept-Encoding: gzip, deflate, br\n'
        b'Accept-Language: en-US,en;q=0.9,ru;q=0.8,ru-RU;q=0.7\n'
        b'Cache-Control: no-cache\n'
        b'Connection: keep-alive\n'
        b'Cookie: token=a0966813f9b27b2a545c75966fd87815660787a3; '
        b'person_pk=1; session=bc8145dc-7e09-46f5-b5fa-789863559f3a. '
        b'EetDaRq0uVnaC8vMKj2YhEYL5Fs; '
        b'csrftoken=njiUhm1sab5u2zOuaa9oHluQay6HOy11c'
        b'J5so09np8mFEF78rk2gzbF7QgsGr8Ox; '
        b'sessionid=vva6mb5l3ugbzxljtorsjl449xn2cco0\n'
        b'Host: localhost:8001\n'
        b'Pragma: no-cache\n'
        b'Sec-Fetch-Dest: document\n'
        b'Sec-Fetch-Mode: navigate\n'
        b'Sec-Fetch-Site: none\n'
        b'Sec-Fetch-User: ?1\n'
        b'Upgrade-Insecure-Requests: 1\n'
        b'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        b'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36\n'
        b'sec-ch-ua: "Google Chrome";v="119", "Chromium";v="119", '
        b'"Not?A_Brand";v="24"\n'
        b'sec-ch-ua-mobile: ?0\n'
        b'sec-ch-ua-platform: "macOS"\n'
    )


@pytest.mark.asyncio
async def test_not_existing_url(http_get_request):
    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()
    assert response == (
        b'HTTP/1.0 200\n'
        b'Access-Control-Allow-Origin: *\n'
        b'Access-Control-Allow-Methods: POST, GET, OPTIONS\n'
        b'Access-Control-Allow-Headers: origin, content-type, accept\n'
        b'Access-Control-Allow-Credentials: true\n'
        b'Access-Control-Max-Age: 86400\n'
        b'Content-Type: application/json;charset=UTF-8\n\n'
        b'404 not found'
    )


@pytest.mark.asyncio
async def test_existing_url(http_get_request):
    http_get_request = http_get_request.replace(b'/users/', b'/test/')
    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()
    assert response == (
        b'HTTP/1.0 200\n'
        b'Access-Control-Allow-Origin: *\n'
        b'Access-Control-Allow-Methods: POST, GET, OPTIONS\n'
        b'Access-Control-Allow-Headers: origin, content-type, accept\n'
        b'Access-Control-Allow-Credentials: true\n'
        b'Access-Control-Max-Age: 86400\n'
        b'Content-Type: application/json;charset=UTF-8\n\n'
        b'test'
    )

