# -*- coding: utf-8 -*-

import asyncio

import httptools

import actionslog as log
from ModSecurity import ModSecurityIntervention
from tesla.http_parser_protocol import HttpParserProtocol
from tesla.sized_buffer import SizedBuffer
from tesla.tesla_exception import TeslaException


class Proxy(asyncio.Protocol):
    @classmethod
    def StrToBytes(cls, data):
        if not isinstance(data, bytes):
            return bytes(data, 'utf-8')
        else:
            return data

    @classmethod
    def BytesToStr(cls, data):
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return str(data)

    def __init__(self, dst_host, dst_port, transaction):
        '''
        @param dst_host: str host to connect to
        @param dst_port: int port to connect to
        @param transaction: ModSecurity.Transaction
        '''
        self._dst_host = dst_host
        self._dst_port = dst_port
        self._transport = None
        self._target_transport = None
        self._transaction = transaction
        self._body_processed = False
        if transaction is None:
            self.abort()
            e = TeslaException(
                'Could not create a proxy without a transaction')
            log.error(e, component='ModSecurity')
            raise e

        self._client_buffer = SizedBuffer()
        self._target_buffer = SizedBuffer()

        self._request_url = None

        self._request_parser_handler = HttpParserProtocol()
        self._request_parser_handler.on_url.add_callback(self.on_request_url)
        self._request_parser_handler.on_header.add_callback(
            self.on_request_header)
        self._request_parser_handler.on_headers_complete.add_callback(
            self.on_request_headers_complete)
        self._request_parser_handler.on_body.add_callback(self.on_request_body)
        self._request_parser_handler.on_message_complete.add_callback(
            self._process_buffers)
        self._request_parser_handler.on_message_complete.add_callback(
            self.on_request_message_completed)
        self._request_parser = httptools.HttpRequestParser(
            self._request_parser_handler)

        self._response_parser_handler = HttpParserProtocol()
        self._response_parser_handler.on_header.add_callback(
            self.on_response_header)
        self._response_parser_handler.on_headers_complete.add_callback(
            self.on_response_headers_complete)
        self._response_parser_handler.on_body.add_callback(
            self.on_response_body)
        self._response_parser_handler.on_status.add_callback(
            self.on_response_status)
        self._response_parser_handler.on_message_complete.add_callback(
            self.on_response_message_completed)
        self._response_parser = httptools.HttpResponseParser(
            self._response_parser_handler)

    def cleanup(self):
        self._request_parser_handler.disconnect()
        self._response_parser_handler.disconnect()

    def abort(self):
        if self._transport is not None:
            self._transport.abort()

        if self._target_transport is not None:
            self._target_transport.abort()

    def close(self):
        if self._transport is not None:
            self._transport.close()

        if self._target_transport is not None:
            self._target_transport.close()

    ############################################################################
    #  CLIENT CALLBACKS
    ############################################################################
    def connection_made(self, transport):
        self._transport = transport
        peername = transport.get_extra_info('peername')

        if peername is None or len(peername) < 2:
            e = TeslaException('Invalid peername was returned!')
            log.error(e, peername=peername)
            raise e

        self._client_host = peername[0]
        self._client_port = peername[1]
        log.info(
            'New client',
            client_host=self._client_host,
            client_port=self._client_port)

        sockname = transport.get_extra_info('sockname')

        if sockname is None or len(sockname) < 2:
            e = TeslaException('Invalid sockname was returned!')
            log.error(e, sockname=sockname)
            raise e

        self._transaction.processConnection(
            self._client_host, self._client_port, sockname[0], sockname[1])

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        self._create_target_connection()

    def _create_target_connection(self):
        log.info(
            'Estabilshing connection to target',
            dst_host=self._dst_host,
            dst_port=self._dst_port,
        )
        loop = asyncio.get_event_loop()
        self._target_coro = loop.create_connection(
            lambda: ProxyTarget(self), self._dst_host, self._dst_port)
        task = loop.create_task(self._target_coro)
        task.add_done_callback(self._create_target_connection_callback)
        return task

    def _create_target_connection_callback(self, future):
        if not future.cancelled():
            exc = future.exception()
            if exc is not None:
                # TODO: should we send something to the client?
                log.warn(
                    'Error trying to connect to dst_host',
                    dst_host=self._dst_host,
                    dst_port=self._dst_port)
                self.close()

    def connection_lost(self, exc):
        log.info(
            'Client connection lost',
            client_host=self._client_host,
            client_port=self._client_port,
            reason=exc if exc is not None else 'EOF')

        self._transport = None
        if self._target_transport is not None:
            # Wait buffer to be flushed
            self._process_buffers()
            self._target_transport.close()

    def data_received(self, data):
        log.info(
            'Client sent data',
            client_host=self._client_host,
            client_port=self._client_port,
            length=len(data))

        try:
            self._request_parser.feed_data(data)
        except httptools.HttpParserUpgrade as ex:
            offset = ex.args[0]
            # TODO

    ############################################################################
    #  TARGET CALLBACKS
    ############################################################################
    def target_connection_made(self, transport):
        log.info(
            'Connection to target established',
            dst_host=self._dst_host,
            dst_port=self._dst_port,
        )
        self._target_transport = transport

        self._process_buffers()

    def target_connection_lost(self, exc):
        log.info(
            'Connection to target was lost',
            dst_host=self._dst_host,
            dst_port=self._dst_port,
            reason=exc if exc is not None else 'EOF')

        self._target_transport = None
        if self._transport is not None:
            # Wait buffer to be flushed
            self._transport.close()

    def target_data_received(self, data):
        log.info(
            'Target sent data',
            dst_host=self._dst_host,
            dst_port=self._dst_port,
            length=len(data))

        try:
            self._response_parser.feed_data(data)
        except httptools.HttpParserUpgrade as ex:
            offset = ex.args[0]
            # TODO

    ############################################################################
    #   Request Callbacks
    ############################################################################
    def on_request_url(self, url):
        self._request_url = url

    def _process_url(self):
        url = self._request_url
        self._request_url = None

        if not self._transaction.processURI(
                url, self._request_parser.get_method(),
                self._request_parser.get_http_version()):
            log.warn(
                'ModSecurity could not process URI',
                url=url,
                method=self._request_parser.get_method(),
                http_version=self._request_parser.get_http_version())

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return False

        data = '{method} {url} HTTP/{version}\n'
        data = data.format(
            method=Proxy.BytesToStr(self._request_parser.get_method()),
            url=Proxy.BytesToStr(url),
            version=Proxy.BytesToStr(self._request_parser.get_http_version()))
        self.send_to_target(data)
        return True

    def on_request_header(self, name, value):
        if self._request_url is not None:
            if not self._process_url():
                return

        if not self._transaction.addRequestHeader(name, value):
            log.warn(
                'ModSecurity could not add request header',
                name=name,
                value=value,
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        data = '{}: {}\n'.format(
            Proxy.BytesToStr(name), Proxy.BytesToStr(value))
        self.send_to_target(data)

    def on_request_headers_complete(self):
        log.info('Request headers completed')
        if not self._transaction.processRequestHeaders():
            log.warn(
                'ModSecurity could not process request headers',
                component='ModSecurity')
        # TODO check for upgrade headers

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        self.send_to_target('\n')

    def on_request_body(self, body):
        log.info('Request body received')
        self._body_processed = True
        if not self._transaction.appendRequestBody(body):
            log.warn(
                'ModSecurity could not feed request body',
                component='ModSecurity')

        if not self._transaction.processRequestBody():
            log.warn(
                'ModSecurity could not process request body',
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        self.send_to_target(body)

    ############################################################################
    #   Response Callbacks
    ############################################################################
    def on_response_header(self, name, value):
        if not self._transaction.addResponseHeader(name, value):
            log.warn(
                'ModSecurity could not add response header',
                name=name,
                value=value,
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return
        
        if not value == b'chunked':
            data = '{}: {}\n'.format(
            Proxy.BytesToStr(name), Proxy.BytesToStr(value))

            self.send_to_client(data)

    def on_response_headers_complete(self):
        log.info('Response headers completed')
        if not self._transaction.processResponseHeaders(
                self._response_parser.get_status_code(),
                self._response_parser.get_http_version()):
            log.warn(
                'ModSecurity could not process response headers',
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        self.send_to_client('\n')

    def on_response_body(self, body):
        log.info('Response body received', length=len(body))
        if not self._transaction.appendResponseBody(body):
            log.warn(
                'ModSecurity could not feed response body',
                component='ModSecurity')

        if not self._transaction.processResponseBody():
            log.warn(
                'ModSecurity could not process response body',
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        self.send_to_client(body)

    def on_response_status(self, status):
        log.info('Response status received')

        if not self._transaction.addResponseHeader(
                'HTTP/%s' % self._response_parser.get_http_version(),
                '%s %s' % (self._response_parser.get_status_code(), status)):
            log.warn(
                'ModSecurity could not add response status header',
                status_code=self._response_parser.get_status_code(),
                status=status,
                component='ModSecurity')

        if self._process_intervention():
            log.info('ModSecurity got a disruptive intervention. Skipping')
            return

        data = 'HTTP/{version} {status_code} {status}\n'
        data = data.format(
            version=Proxy.BytesToStr(self._response_parser.get_http_version()),
            status_code=Proxy.BytesToStr(
                self._response_parser.get_status_code()),
            status=Proxy.BytesToStr(status))

        self.send_to_client(data)
    
    def on_request_message_completed(self):
        if not self._body_processed:
            if not self._transaction.processRequestBody():
                log.warn(
                'ModSecurity could not process request body',
                component='ModSecurity')

            if self._process_intervention():
                log.info('ModSecurity got a disruptive intervention. Skipping')
                return

    def on_response_message_completed(self):
        self._process_buffers() 
        self.close()

    ############################################################################
    #   Other
    ############################################################################
    def _flush_buffer(self, buffer, transport):
        length = 0

        if buffer.tell() > 0:
            length = transport.write(buffer.getvalue())
            buffer.seek(0)

        return length

    def _process_buffers(self):
        """
        Make sure the buffers are empty and all data
        are flushed to their destination
        """
        if self._target_transport is not None and \
                not self._target_transport.is_closing():
            self._flush_buffer(self._target_buffer, self._target_transport)

        if self._transport is not None and \
                not self._transport.is_closing():
            self._flush_buffer(self._client_buffer, self._transport)

    def send_to_client(self, data, overwrite=False):
        """
        Send data to the client if possible
        :param list(bytes) data:
        """
        if overwrite:
            self._client_buffer = SizedBuffer()
            self._client_buffer.write(Proxy.StrToBytes(data))
        else:
            self._client_buffer.write(Proxy.StrToBytes(data))

    def send_to_target(self, data):
        """
        Send data to the target if possible
        :param list(bytes) data:
        """
        self._target_buffer.write(Proxy.StrToBytes(data))

    def _process_intervention(self):
        '''
        Process and check if there's a ModSecurity intervention
        :rtype ModSecurityIntervention:
        :return True if we got a disruptive intervention, false otherwise
        '''
        if self._transaction is None:
            e = TeslaException('There\'s no transaction in progress')
            log.error(e)
            return False

        intervention = ModSecurityIntervention()
        if self._transaction.intervention(intervention):

            if intervention.log is not None:
                log.info(intervention.log, component='ModSecurity')

            if intervention.url is not None:
                self.send_redirect_to_client(
                    intervention.url, status_code=intervention.status)
                self._process_buffers()
                self.close()
                return True

            if intervention.status != 200:
                self.send_deny_to_client(intervention.status)
                self._process_buffers()
                self.close()
                return True

            return intervention.disruptive
        else:
            log.debug('ModSecurity found no interventions')

        return False

    def send_redirect_to_client(self, url, status_code=302):
        f = open('etc/templates/302.txt', mode='r')
        redirect_template = f.read()
        f.close()

        body = redirect_template
        print('---------------------------- redirect')
        self.send_to_client(body, overwrite=True)

    def send_deny_to_client(self, status_code=403):
        f = open('etc/templates/403.txt', mode='r')
        forbidden_template = f.read()
        f.close()

        body = forbidden_template
        self.send_to_client(body, overwrite=True)


class ProxyTarget(asyncio.Protocol):
    """
    This is an internal class and the main purpose is to create
    a proxy callback-based with the target. Idealy all events
    here must be emitted to and treated in `Proxy`.
    """

    def __init__(self, parent):
        self._parent = parent

    def connection_made(self, transport):
        self._parent.target_connection_made(transport)

    def connection_lost(self, exc):
        self._parent.target_connection_lost(exc)

    def data_received(self, data):
        self._parent.target_data_received(data)
