import asyncio

import pytest
import uvloop

from .mock_tcp import MockTcpClient, MockTcpServer, MockTransport


@pytest.fixture
def dst_port(unused_tcp_port):
    return unused_tcp_port


@pytest.fixture
def event_loop():
    '''
    Override so we can use the same event loop used by tesla (attached to the asyncio lib)
    '''
    if not isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return asyncio.get_event_loop()


@pytest.yield_fixture
def tcp_client():
    client = MockTcpClient()
    yield client
    client.close()


@pytest.yield_fixture
def tcp_server():
    server = MockTcpServer()
    yield server
    server.close()


@pytest.fixture
def transport_factory(mocker, unused_tcp_port):
    info = {
        'peername': ('127.0.0.1', unused_tcp_port),
        'sockname': ('127.0.0.1', 9090),
    }

    def create(extra_info={}):
        new_info = {**info, **extra_info}
        return MockTransport(mocker, new_info)

    return create
