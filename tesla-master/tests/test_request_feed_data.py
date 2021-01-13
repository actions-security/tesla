import pytest


def test_request_feed_data_on_url(proxy, mocker):
    mocker.patch.object(proxy, 'send_to_target')
    stub = mocker.stub(name='on_request_url')
    proxy._request_parser_handler.on_url.add_callback(stub)

    proxy._request_parser.feed_data(b'GET /index.html HTTP/1.0')

    stub.assert_called_once_with(b'/index.html')
    assert proxy.send_to_target.call_count == 0


def test_request_feed_data_on_header(proxy, mocker, http_request):
    mocker.patch.object(proxy, 'send_to_target')
    mocker.spy(proxy, '_process_url')

    stub = mocker.stub(name='on_request_header')
    proxy._request_parser_handler.on_header.add_callback(stub)

    proxy._request_parser.feed_data(http_request)
    assert proxy._process_url.call_count == 1
    stub.assert_called_with(b'Upgrade-Insecure-Requests', b'1')


def test_request_feed_data_on_headers_complete(proxy, mocker, http_request):
    mocker.patch.object(proxy, 'send_to_target')

    stub = mocker.stub(name='on_request_headers_complete')
    proxy._request_parser_handler.on_headers_complete.add_callback(stub)

    proxy._request_parser.feed_data(http_request)

    assert stub.call_count == 1
    assert proxy.send_to_target.call_count == 10


def test_request_feed_data_on_body(proxy, mocker, http_request_with_body):
    mocker.patch.object(proxy, 'send_to_target')

    stub = mocker.stub(name='on_request_body')
    proxy._request_parser_handler.on_body.add_callback(stub)

    proxy._request_parser.feed_data(http_request_with_body)

    assert stub.call_count == 1
    assert proxy.send_to_target.call_count == 13
