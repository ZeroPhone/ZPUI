from functools import wraps

KEY_PRESSED = 1
KEY_RELEASED = 0
KEY_HELD = 2

def cb_needs_key_state(callback, new_function=False):
    """
    Marks a callable with an attribute that lets the input system know that, on key event,
    key state should be passed to this callable. As a result, the callable will also be called
    on key press, hold and release, instead of only being called on a keypress, as is the default.

    By default, just sets an attribute on the callable object passed - if that fails
    (i.e. you have a lambda or a class method), pass ``new_function=True`` keyword argument
    to wrap the callable.
    """
    if new_function:
        @wraps(callback)
        def func(*args, **kwargs):
            return callback(*args, **kwargs)
        func.zpui_icb_pass_key_state = True
        return func
    # Creating a new function not requested, just modify in-place
    if hasattr(callback, "__func__"):
        callback.__func__.zpui_icb_pass_key_state = True
    else:
        callback.zpui_icb_pass_key_state = True
    return callback

def get_all_available_keys(i):
    """
    Given an input proxy, returns a list of all keys that are available
    from all the input drivers currently attached.
    """
    l = []
    [l.extend(v) for v in i.available_keys.values()]
    return list(set(l))
