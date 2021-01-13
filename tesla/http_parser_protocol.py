from tesla.event_dispatcher import EventDispatcher


class HttpParserProtocol(object):
    def __init__(self):
        self.on_message_begin = EventDispatcher()

        self.on_url = EventDispatcher()

        self.on_header = EventDispatcher()

        self.on_headers_complete = EventDispatcher()

        self.on_body = EventDispatcher()

        self.on_message_complete = EventDispatcher()

        self.on_chunk_header = EventDispatcher()

        self.on_chunk_complete = EventDispatcher()

        self.on_status = EventDispatcher()

    def disconnect(self):
        self.on_message_begin.clear()
        self.on_url.clear()
        self.on_header.clear()
        self.on_headers_complete.clear()
        self.on_body.clear()
        self.on_message_complete.clear()
        self.on_chunk_header.clear()
        self.on_chunk_complete.clear()
        self.on_status.clear()
