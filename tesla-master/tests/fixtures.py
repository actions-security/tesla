import os

import pytest

import ModSecurity
from tesla.main import Tesla
from tesla.proxy import Proxy


@pytest.fixture
def log():
    import argparse
    import actionslog as log
    ap = argparse.ArgumentParser()
    log.init(ap, 'mock_log')
    log.setup(args=[])


@pytest.fixture
def tesla(log):
    tesla = Tesla()
    return tesla


@pytest.fixture
def modsecurity():
    return ModSecurity.ModSecurity()


@pytest.fixture
def modsecurity_rules(tmpdir):
    rules = ModSecurity.Rules()
    rules.loadFromUri('etc/config-logs.conf')
    rules.load('SecTmpDir %s' % str(tmpdir))
    rules.load('SecDataDir %s' % str(tmpdir))
    rules.load('SecDebugLog %s/modsec_debug.log' % str(tmpdir))
    return rules


@pytest.fixture
def modsecurity_transaction(modsecurity, modsecurity_rules):
    return ModSecurity.Transaction(modsecurity, modsecurity_rules)


@pytest.fixture
def modsecurity_intervention():
    return ModSecurity.ModSecurityIntervention()


@pytest.yield_fixture
def proxy(mocker, log, modsecurity_transaction, dst_port):
    p = Proxy('localhost', dst_port, modsecurity_transaction)
    yield p
    p.cleanup()


@pytest.fixture
def http_request():
    with open('etc/http_request.txt') as f:
        return bytes(f.read(), 'utf-8')


@pytest.fixture
def http_request_with_body():
    with open('etc/http_request_with_body.txt') as f:
        return bytes(f.read(), 'utf-8')


@pytest.fixture
def http_response():
    with open('etc/http_response.txt') as f:
        return bytes(f.read(), 'utf-8')
