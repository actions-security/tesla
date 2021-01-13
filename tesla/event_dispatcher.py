class EventDispatcher(object):
    '''
    Simple Event Dispatcher
    Events can be dispatcher to many subscribers
    '''

    def __init__(self):
        self._subscribers = []

    def add_callback(self, func):
        '''
        Add a callback listener to this event dispatcher
        '''
        self._subscribers.append(func)

    def remove_callback(self, func):
        '''
        Remove a callback from this event dispatcher
        '''
        self._subscribers.remove(func)

    def clear(self):
        '''
        Removes all subscribers from this event dispatcher
        '''
        self._subscribers.clear()

    def __call__(self, *args, **kwargs):
        for sub in self._subscribers:
            sub(*args, **kwargs)
