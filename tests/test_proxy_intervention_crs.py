import pytest

import ModSecurity
from tesla.proxy import Proxy


def test_intervention_disruptive_connection_made(
        mocker, proxy, modsecurity_rules, transport_factory):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRule REMOTE_ADDR "@ipMatch 127.0.0.1" "deny,phase:0,id:35,msg:\'Blocked\'"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    mocker.patch.object(proxy, '_create_target_connection')

    proxy.connection_made(transport_factory())

    proxy._create_target_connection.assert_not_called()


def test_intervention_disruptive_request_url(mocker, proxy, modsecurity_rules,
                                             transport_factory):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRule REQUEST_URI "@streq /attack.php" "id:1,phase:1,t:lowercase,deny"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_target')

    # This is really a limitation of httptools
    # We can only add pending parsed url after adding a header
    # although we make sure to check for interventions on the uri
    # before processing parsed header
    proxy.data_received(b'GET /attack.php HTTP/1.1\n')
    proxy.data_received(b'Connection: Close\n\n')

    assert proxy.send_to_target.call_count == 2
    proxy.send_to_target.reset_mock()

    proxy.on_request_headers_complete()

    proxy.send_to_target.assert_not_called()


def test_intervention_disruptive_request_header(
        mocker, proxy, modsecurity_rules, transport_factory):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRule REQUEST_HEADERS:User-Agent "nikto" "log,deny,id:107,msg:\'Nikto Scanners Identified\'"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_target')

    proxy.data_received(b'GET /index.html HTTP/1.1\n')
    proxy.data_received(b'User-Agent: nikto\n\n')

    assert proxy.send_to_target.call_count == 2
    proxy.send_to_target.reset_mock()

    proxy.on_request_headers_complete()

    proxy.send_to_target.assert_not_called()


def test_intervention_disruptive_request_body(mocker, proxy, modsecurity_rules,
                                              transport_factory,
                                              http_request_with_body):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRequestBodyAccess On\n'
    rule += 'SecRule REQUEST_BODY "@contains hello" "id:43,phase:2,deny"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_target')

    proxy.data_received(http_request_with_body)

    # request line + 10 headers + \n
    # do not call body
    assert proxy.send_to_target.call_count == 12


def test_intervention_disruptive_response_status(
        mocker, proxy, modsecurity_rules, transport_factory):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRule RESPONSE_STATUS "@streq 503" "phase:3,id:58,deny"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_client')

    proxy.target_data_received(b'HTTP/1.1 503 error\n')
    # We send the data here
    assert proxy.send_to_client.call_count == 1
    proxy.send_to_client.reset_mock()

    # Finish response headers
    proxy.target_data_received(b'\n')

    f = open('etc/templates/403.txt', mode='r')
    forbidden_template = f.read()
    f.close()

    proxy.send_to_client.assert_called_once_with(
        forbidden_template, overwrite=True)


def test_intervention_disruptive_response_header(
        mocker, proxy, modsecurity_rules, transport_factory):
    rule = 'SecRuleEngine On\n'
    rule += 'SecRule RESPONSE_HEADERS:X-Cache "MISS" "phase:3,id:55,deny"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_client')
    mocker.spy(proxy, 'on_response_headers_complete')

    proxy.target_data_received(b'HTTP/1.1 200 OK\n')
    proxy.target_data_received(b'X-Cache: MISS\n\n')
    proxy.on_response_headers_complete.assert_not_called()

    # Called two times for two headers above
    assert proxy.send_to_client.call_count == 3
    proxy.send_to_client.reset_mock()

    # Finish response headers
    proxy.on_response_headers_complete()
    
    f = open('etc/templates/403.txt', mode='r')
    forbidden_template = f.read()
    f.close()

    proxy.send_to_client.assert_called_once_with(
        forbidden_template, overwrite=True)


def test_intervention_disruptive_response_body(
        mocker, proxy, modsecurity_rules, transport_factory, http_response):
    rule = 'SecRuleEngine On\n'
    rule += 'SecResponseBodyAccess On\n'
    rule += 'SecRule RESPONSE_BODY "Hello" "deny,phase:4,id:54"'
    assert modsecurity_rules.load(rule) > 0, modsecurity_rules.getParserError()

    proxy.connection_made(transport_factory())

    mocker.patch.object(proxy, 'send_to_client')

    proxy.target_data_received(http_response)

    # 1 response status, 4 headers, \n
    # do not call body
    assert proxy.send_to_client.call_count == 7

    f = open('etc/templates/403.txt', mode='r')
    forbidden_template = f.read()
    f.close()

    proxy.send_to_client.assert_called_with(
        forbidden_template, overwrite=True)
