import asyncio


class MockTransport(object):
    def __init__(self, mocker, extra_info, data_out=None):
        self.data_in = []
        self.data_out = data_out
        self.extra_info = extra_info
        self.calls = {}

        self._mocker = mocker

    def write(self, data):
        self.data_in.append(data)

    def get_extra_info(self, key):
        return self.extra_info.get(key, None)

    def is_closing(self):
        return False

    def __getattr__(self, name):
        return self.calls.setdefault(name, self._mocker.stub(name=name))


class MockTcpClient(object):
    def __init__(self):
        self._writer = None
        self._reader = None

    async def connect(self, host, port):
        self._reader, self._writer = await asyncio.open_connection(host, port)
        return self._reader, self._writer

    def close(self):
        if self._writer is not None:
            self._writer.close()

    async def write(self, data, write_eof=True):
        self._writer.write(data)
        await self._writer.drain()
        if write_eof:
            self.write_eof()

    def write_eof(self):
        self._writer.write_eof()

    async def read(self):
        data = b''
        while True:
            b = await self._reader.read(128)
            if b:
                data += b
            else:
                break
        return data


class MockTcpServer(object):
    def __init__(self):
        self._reader = None
        self._writer = None
        self._server = None

        self._has_client = asyncio.Event()

    async def listen(self, host, port):
        self._has_client.clear()
        self._server = await asyncio.start_server(self.handle, host, port)

    async def handle(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self._has_client.set()

    def wait_client(self):
        return self._has_client.wait()

    async def read(self):
        data = b''
        if self._reader is None:
            raise Exception('No connected instance')
        while True:
            b = await self._reader.read(128)
            if b:
                data += b
            else:
                break

        return data

    async def write(self, data, write_eof=True):
        self._writer.write(data)
        await self._writer.drain()
        if write_eof:
            self.write_eof()

    def write_eof(self):
        self._writer.write_eof()

    def close(self):
        if self._server is not None:
            self._server.close()
