from actions import ContextSwitchAction, FirstBootAction

class ActionManager(object):
    action_name_delimiter = "%"

    def __init__(self, cm):
        self.actions = {}
        self.cm = cm

    def register_action(self, action):
        name = action.full_name
        while self.action_name_delimiter in name:
            name = name.remove(self.action_name_delimiter)
        self.actions[name] = action
        # Setting a usable callback for ContextSwitchActions
        if isinstance(action, ContextSwitchAction) \
          and getattr(action, "func", None) is None:
            action.func = lambda x=action.target_context: self.cm.switch_to_context(x)

    def register_firstboot_action(self, action, context_alias):
        name = action.name
        if context_alias:
            name = self.action_name_delimiter.join([context_alias, name])
        self.actions[name] = action

    def get_actions(self):
        return self.actions

    def get_firstboot_actions(self):
        return dict([(name, action) for name, action in self.actions.items() if isinstance(action, FirstBootAction)])
