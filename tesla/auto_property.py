# -*- coding: utf-8 -*-


def autoproperty(**kwargs):

    hasGet = True
    hasSet = True
    hasDel = True
    baseName = ''
    innerName = '_{}'
    defaultValue = None

    for key, value in kwargs.items():
        if key == 'hasGet':
            hasGet = value
        elif key == 'hasSet':
            hasSet = value
        elif key == 'hasDel':
            hasDel = value
        else:
            baseName = key
            innerName = innerName.format(key)
            defaultValue = value

    def _get(obj):
        return getattr(obj, innerName, defaultValue)

    def _set(obj, v):
        setattr(obj, innerName, v)

    def _del(obj):
        delattr(obj, innerName)

    def decorator(cls):
        prop = property(_get if hasGet else None, _set if hasSet else None,
                        _del if hasDel else None)

        setattr(cls, baseName, prop)

        props = getattr(cls, '__properties__', [])
        props.insert(0, baseName)
        setattr(cls, '__properties__', props)

        return cls

    return decorator
