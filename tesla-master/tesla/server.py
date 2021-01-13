# -*- coding: utf-8 -*-
import asyncio
import ssl

import actionslog as log
from tesla.auto_property import autoproperty
from tesla.proxy import Proxy


@autoproperty(name='')
@autoproperty(src_host='0.0.0.0')
@autoproperty(src_port=9090)
@autoproperty(dst_host='')
@autoproperty(dst_port=0)
@autoproperty(ssl=False)
@autoproperty(cert='')
@autoproperty(key='')
class Server(object):
    def __init__(self,
                 name,
                 src_host,
                 src_port,
                 dst_host,
                 dst_port,
                 use_ssl=False,
                 cert='',
                 key='',
                 proxy_creator_func=None):
        '''
        @param name: str name of the server
        @param src_host: str host to bind the server
        @param src_port: int port to bind the server
        @param dst_host: str host to connect to
        @param dst_port: int port to connect to
        @param ssl: bool if this server should use ssl
        @param cert: str path to the certificate
        @param key: str path to the private key
        @param proxy_creator_func: callable(dst_host: str, dst_port: int) callable to
            creator proxy objects when needed, if none a default will be used
        '''
        self.name = name
        self.src_host = src_host
        self.src_port = src_port
        self.dst_host = dst_host
        self.dst_port = dst_port
        self.ssl = use_ssl
        self.cert = cert
        self.key = key
        self._proxy_creator_func = proxy_creator_func or self._default_proxy_creator

        if self.ssl:
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            self._ssl_context.load_cert_chain(self.cert, self.key)
        else:
            self._ssl_context = None

        log.info(
            'Starting server at {}:{} to {}:{}'.format(
                self.src_host, self.src_port, self.dst_host, self.dst_port),
            src_host=self.src_host,
            src_port=self.src_port,
            dst_host=self.dst_host,
            dst_port=self.dst_port,
        )
        loop = asyncio.get_event_loop()
        self._coro = loop.create_server(
            lambda: self._proxy_creator_func(self.dst_host, self.dst_port),
            self.src_host,
            self.src_port,
            ssl=self._ssl_context,
            reuse_address=True,
            reuse_port=True)
        self._server_future = loop.create_task(self._coro)
        log.info(
            'Server is ready at {}:{} to {}:{}'.format(
                self.src_host, self.src_port, self.dst_host, self.dst_port),
            src_host=self.src_host,
            src_port=self.src_port,
            dst_host=self.dst_host,
            dst_port=self.dst_port,
        )

    def _default_proxy_creator(self, dst_host, dst_port):
        p = Proxy(dst_host, dst_port)
        return p

    async def ensure_serving(self):
        await self._server_future
