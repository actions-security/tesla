import pytest

import ModSecurity


@pytest.fixture(params=[True, False])
def disruptive(request):
    return request.param


def test_intervention_disruptive_connection_made(
        proxy, mocker, transport_factory, disruptive):
    mocker.patch.object(
        proxy, '_process_intervention', return_value=disruptive)
    mocker.patch.object(proxy, '_create_target_connection')

    proxy.connection_made(transport_factory())
    assert not proxy._create_target_connection.called == disruptive


@pytest.mark.parametrize('method,method_args', [
    ('on_request_header', ['Connection', 'Close']),
    ('on_request_headers_complete', []),
    ('on_request_body', [b'hello world']),
])
def test_intervention_disruptive_request_method(
        proxy, mocker, transport_factory, disruptive, method, method_args):
    mocker.patch.object(
        proxy, '_process_intervention', return_value=disruptive)
    mocker.patch.object(proxy, 'send_to_target')

    getattr(proxy, method)(*method_args)
    assert not proxy.send_to_target.called == disruptive


@pytest.mark.parametrize('method,method_args', [
    ('on_response_header', ['Connection', 'Close']),
    ('on_response_headers_complete', []),
    ('on_response_body', [b'hello world']),
    ('on_response_status', [404]),
])
def test_intervention_disruptive_response_method(
        proxy, mocker, transport_factory, disruptive, method, method_args):
    mocker.patch.object(
        proxy, '_process_intervention', return_value=disruptive)
    mocker.patch.object(proxy, 'send_to_client')

    getattr(proxy, method)(*method_args)
    assert not proxy.send_to_client.called == disruptive
