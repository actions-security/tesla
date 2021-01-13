import pytest
import requests


@pytest.mark.parametrize(
    'args',
    [
        [],  # no args
        ['localhost'],  # no dst port, no rule set
        ['a', 'a'],  # invalid dst port, no rule set
        ['127.0', 'a', 'a'],  # invalid dst port
        ['a', '8080', 'a', '--src-port=a'],  # invalid src port
    ])
def test_invalid_args(tesla, mocker, args):
    mocker.patch.object(tesla, '_create_server')
    with pytest.raises(SystemExit):
        tesla.setup(args=args)


def test_invalid_args_src_host(tesla, mocker):
    '''
    --src-host is handled differently
    '''
    mocker.patch.object(tesla, '_create_server')
    args = ['a', '8080', 'a', '--src-port=9090',
            '--src-host=a']  # invalid src host
    from tesla.tesla_exception import TeslaException
    with pytest.raises(TeslaException):
        tesla.setup(args=args)


@pytest.mark.parametrize(
    'rulesets',
    [['etc/owasp-crs/rules/*.conf'], ['etc/basic_rules.conf'],
     [
         'etc/modsecurity.conf', 'etc/owasp-crs/crs-setup.conf.example',
         'etc/owasp-crs/rules/*.conf*'
     ]])
def test_load_rule_set(tesla, mocker, rulesets):
    mocker.patch.object(tesla, '_create_server')
    args = ['127.0.0.1', '8080', *rulesets]

    mocker.patch.object(tesla, '_load_modsec_rule_from_filename')
    tesla.setup(args=args)

    import glob
    files = []
    for ruleset in rulesets:
        files.extend(glob.glob(ruleset, recursive=True))

    assert tesla._load_modsec_rule_from_filename.call_count == len(files)

    for f in files:
        tesla._load_modsec_rule_from_filename.assert_any_call(f)


@pytest.mark.parametrize(
    'args, xargs',
    [
        # (args, xargs)
        # ([*], [src-host, src-port, dst-host, dst-port] )
        (['localhost', '80'], ['0.0.0.0', 9090, 'localhost', 80]),
        (['localhost', '80', '--src-port=91'],
         ['0.0.0.0', 91, 'localhost', 80]),
        (['localhost', '8080', '--src-host=127.0.1.1'],
         ['127.0.1.1', 9090, 'localhost', 8080]),
        (['localhost', '80', '--src-host=127.0.1.1', '--src-port=9192'],
         ['127.0.1.1', 9192, 'localhost', 80]),
    ])
def test_create_server(tesla, mocker, args, xargs):
    mocker.patch.object(tesla, '_create_server')
    tesla.setup(args=[*args, 'etc/basic_rules.conf'])

    tesla._create_server.assert_called_once_with(
        *xargs, proxy_creator_func=tesla._create_proxy)


@pytest.mark.parametrize('addr, expected', [
    ('127.0.0.1', True),
    ('a', False),
    ('::0', True),
    ('fe80::e328:672b:bba5:9eea', True),
    ('fe80::e328:672b:bba5:9eea:', False),
    ('127.0.a.1', False),
])
def test_is_valid_address(tesla, addr, expected):
    assert tesla._is_valid_address(addr) == expected


@pytest.mark.asyncio
async def test_create_proxy(tesla, tcp_client, unused_tcp_port, mocker,
                            event_loop):
    args = [
        'localhost', '80', 'etc/basic_rules.conf',
        '--src-port=' + str(unused_tcp_port)
    ]
    mocker.patch.object(tesla, '_create_proxy')

    # the server is schedule in the event loop
    tesla.setup(args=args)
    await tesla.server.ensure_serving()

    await tcp_client.connect('localhost', unused_tcp_port)

    tesla._create_proxy.assert_called_once_with('localhost', 80)


@pytest.mark.asyncio
async def test_echo_proxy(tesla, httpserver, unused_tcp_port, mocker,
                          event_loop):
    content = b'File not found!'
    code = 404
    headers = {'x-my-custom-header': 'abc123'}

    httpserver.serve_content(content, code, headers)
    dst_port = httpserver.server_address[1]
    src_port = unused_tcp_port

    args = [
        'localhost',
        str(dst_port), 'etc/basic_rules.conf', '--src-port=' + str(src_port)
    ]
    tesla.setup(args=args)
    await tesla.server.ensure_serving()

    url = 'http://localhost:{}/index.html'.format(str(src_port))
    out = await event_loop.run_in_executor(None, requests.get, url)
    assert out.content == content
    assert out.status_code == code
    for k, v in headers.items():
        assert k in out.headers
        assert v == headers[k]


@pytest.mark.asyncio
async def test_dst_refused(tesla, unused_tcp_port_factory, mocker, event_loop):
    dst_port = unused_tcp_port_factory()
    src_port = unused_tcp_port_factory()

    args = [
        'localhost',
        str(dst_port), 'etc/basic_rules.conf', '--src-port=' + str(src_port)
    ]
    tesla.setup(args=args)
    await tesla.server.ensure_serving()

    url = 'http://localhost:{}/index.html'.format(str(src_port))
    with pytest.raises(requests.exceptions.ConnectionError):
        await event_loop.run_in_executor(None, requests.get, url)
