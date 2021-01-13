import pytest


def test_response_feed_data_on_status(proxy, mocker):
    mocker.patch.object(proxy, 'send_to_client')
    stub = mocker.stub(name='on_response_status')
    proxy._response_parser_handler.on_status.add_callback(stub)

    proxy._response_parser.feed_data(b'HTTP/1.1 200 OK\n')

    stub.assert_called_once_with(b'OK')
    assert proxy.send_to_client.call_count == 1


def test_response_feed_data_on_header(proxy, mocker, http_response):
    mocker.patch.object(proxy, 'send_to_client')

    stub = mocker.stub(name='on_response_header')
    proxy._response_parser_handler.on_header.add_callback(stub)

    proxy._response_parser.feed_data(http_response)

    assert stub.call_count == 4
    # status + 4 headers + \n + body
    assert proxy.send_to_client.call_count == 7


def test_response_feed_data_on_headers_complete(proxy, mocker, http_response):
    mocker.patch.object(proxy, 'send_to_client')

    stub = mocker.stub(name='on_response_headers_complete')
    proxy._response_parser_handler.on_headers_complete.add_callback(stub)

    proxy._response_parser.feed_data(http_response)

    assert stub.call_count == 1
    assert proxy.send_to_client.call_count == 7


def test_response_feed_data_on_body(proxy, mocker, http_response):
    mocker.patch.object(proxy, 'send_to_client')

    stub = mocker.stub(name='on_response_body')
    proxy._response_parser_handler.on_body.add_callback(stub)

    proxy._response_parser.feed_data(http_response)

    assert stub.call_count == 1
    assert proxy.send_to_client.call_count == 7
