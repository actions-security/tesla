import pytest

import ModSecurity


@pytest.mark.alloc
@pytest.mark.parametrize('n', range(20))
def test_allocation(proxy, n):
    assert proxy


def test_on_request_url(mocker, proxy):
    '''
    url, method and http version are only sent
    after the first header is received. This tests that
    '''
    mocker.patch.object(proxy, 'send_to_target')
    proxy.on_request_url('/index.html')
    assert proxy.send_to_target.call_count == 0


def test_on_request_header(mocker, proxy):
    mocker.patch.object(proxy, 'send_to_target')
    proxy.on_request_header('Connection', 'close')

    expected = 'Connection: close\n'
    proxy.send_to_target.assert_called_once_with(expected)

    proxy.on_request_headers_complete()

    assert proxy.send_to_target.call_count == 2
    proxy.send_to_target.assert_called_with('\n')


def test_on_request_header_after_url(mocker, proxy):
    mocker.patch.object(proxy, 'send_to_target')
    proxy.on_request_url('/index.html')
    proxy.on_request_header('Connection', 'close')

    expected = 'Connection: close\n'
    expected_url = 'DELETE /index.html HTTP/0.0\n'
    assert proxy.send_to_target.call_count == 2
    proxy.send_to_target.assert_any_call(expected)
    proxy.send_to_target.assert_any_call(expected_url)


def test_on_request_body(mocker, proxy):
    body = '{"custom_data": "123b"}'

    mocker.patch.object(proxy, 'send_to_target')
    proxy.on_request_body(body)
    proxy.send_to_target.assert_called_once_with(body)


def test_on_response_status(mocker, proxy):
    mocker.patch.object(proxy, 'send_to_client')
    proxy.on_response_status(b'404')

    proxy.send_to_client.assert_called_once_with('HTTP/0.0 0 404\n')


def test_on_response_header(mocker, proxy):
    mocker.patch.object(proxy, 'send_to_client')

    expected = 'Content-Type: text/html; charset=UTF-8\n'
    proxy.on_response_header('Content-Type', 'text/html; charset=UTF-8')
    proxy.send_to_client.assert_called_once_with(expected)

    proxy.on_response_headers_complete()

    assert proxy.send_to_client.call_count == 2
    proxy.send_to_client.assert_called_with('\n')


def test_on_response_body(mocker, modsecurity_transaction, proxy):
    body = 'Hello'
    mocker.patch.object(proxy, 'send_to_client')
    proxy.on_response_body(body)
    proxy.send_to_client.assert_called_once_with(body)


@pytest.mark.asyncio
async def test_tcp_send_to_target(proxy, dst_port, tcp_server, http_request):
    await tcp_server.listen('127.0.0.1', dst_port)

    await proxy._create_target_connection()
    proxy.send_to_target(http_request)
    proxy._process_buffers()
    proxy.close()

    server_data = await tcp_server.read()

    assert server_data == http_request


def test_tcp_send_to_client(proxy, dst_port, http_response, transport_factory,
                            mocker):
    transport = transport_factory()

    mocker.patch.object(proxy, '_create_target_connection')
    proxy.connection_made(transport)

    assert proxy._create_target_connection.called

    proxy.send_to_client(http_response)
    proxy._process_buffers()

    assert b''.join(transport.data_in) == http_response


@pytest.mark.asyncio
async def test_tcp_data_received(proxy, dst_port, tcp_server, http_request,
                                 transport_factory):
    transport = transport_factory()
    await tcp_server.listen('127.0.0.1', dst_port)

    proxy.connection_made(transport)

    await proxy._create_target_connection()
    proxy.data_received(http_request)
    proxy.close()

    server_data = await tcp_server.read()

    assert server_data == http_request


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main(args=['-m', 'new']))
