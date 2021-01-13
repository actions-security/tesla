from io import BytesIO


class SizedBuffer(BytesIO):
    def __init__(self, soft_limit=1024, hard_limit=10000, initial_bytes=None):
        self._soft_limit = soft_limit
        self._hard_limit = hard_limit

        super().__init__(initial_bytes)

    @property
    def soft_limit(self):
        return self._soft_limit

    @soft_limit.setter
    def soft_limit(self, v):
        self._soft_limit = v

    @property
    def hard_limit(self):
        return self._hard_limit

    @hard_limit.setter
    def hard_limit(self, v):
        self._hard_limit = v

    @property
    def soft_reached(self):
        return self.tell() > self.soft_limit

    @property
    def hard_reached(self):
        return self.tell() > self.hard_limit

    def write(self, data):
        if self.tell() > self._hard_limit:
            raise IOError('SizedBuffer reached its hard limited')

        return super().write(data)
