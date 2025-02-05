import unittest

class Action(object):
    name = None
    func = None
    type = None
    default_affects_backlight = True
    default_will_context_switch = True

    used_kwargs = []

    def __init__(self, name, func, type="simple", \
                 menu_name = None, description = None, \
                 affects_backlight = None, \
                 will_context_switch = None, \
                 **kwargs):
        self.name = name
        self.func = func
        self.type = type
        self.menu_name = menu_name
        self.description = description
        self.will_context_switch = will_context_switch \
          if will_context_switch is not None \
          else self.default_will_context_switch
        self.affects_backlight = affects_backlight \
          if affects_backlight is not None \
          else self.default_affects_backlight
        kwargs.pop("context", None)
        self.set_unused_kwargs_as_properties(kwargs)

    def set_unused_kwargs_as_properties(self, kwargs):
        for key, value in kwargs.items():
            if key not in self.used_kwargs:
                setattr(self, key, value)

class BackgroundAction(Action):
    default_affects_backlight = False
    default_will_context_switch = False

class FirstBootAction(Action):
    depends = None
    not_on_emulator = None

class ContextSwitchAction(Action):
    def __init__(self, name, func, **kwargs):
       super(ContextSwitchAction, self).__init__(name, func, **kwargs)
       if not hasattr(self, "target_context"):
          self.target_context = None

class KeyAction(Action):
    used_kwargs = ["key", "key_state"]
    def __init__(self, *args, **kwargs):
       key = kwargs.pop("key")
       state = kwargs.pop("key_state", None)
       self.key = key
       self.key_state = state
       super(KeyAction, self).__init__(*args, **kwargs)

# Tests

class TestActions(unittest.TestCase):
    def test_combined_contextswitch_key_action(self):
        """Testing whether inheritance properly combines __init__ of both classes."""
        pass
        cls = type("TestAction", (ContextSwitchAction, KeyAction), {})
        action = cls("testaction", lambda x:True, target_context="main", key="KEY_ENTER", key_state=0)
        assert(getattr(action, "target_context", None) == "main")
        assert(getattr(action, "key", None) == "KEY_ENTER")
        assert(getattr(action, "key_state", None) == 0)
        action = cls("testaction", lambda x:True, target_context="main", key="KEY_ENTER")
        assert(getattr(action, "target_context", None) == "main")
        assert(getattr(action, "key", None) == "KEY_ENTER")

if __name__ == "__main__":
    unittest.main()
