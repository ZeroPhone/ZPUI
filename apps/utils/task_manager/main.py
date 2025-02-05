from apps import ZeroApp
from ui import Menu

class TaskManager(ZeroApp):

    menu_name = "Task manager"

    def set_context(self, c):
        self.context = c

    def get_contexts(self):
        return self.context.list_contexts()

    def task_menu(self, context_desc):
        name = context_desc["name"]
        mc = [[["Menu name:", str(context_desc["menu_name"])]],
              [["Context name:", name]],
              [["State:", context_desc["state"]]],
              [["Previous context:", str(context_desc["previous_context"])]],
              [["Switch to", "context"], lambda: self.context.request_switch(name)]]
        Menu(mc, self.i, self.o, entry_height=2, name="Task manager {} context menu".format(name)).activate()

    def on_start(self):
        def get_task_menu_c():
            mc = []
            contexts = self.get_contexts()
            running_c = [c for c in contexts if c["state"] == "running"]
            inactive_c = [c for c in contexts if c["state"] == "inactive"]
            nonthreaded_c = [c for c in contexts if c["state"] == "non-threaded"]
            context_types = [["Running", running_c],
                             ["Inactive", inactive_c],
                             ["Non-threaded", nonthreaded_c]]
            for name, l in context_types:
                if l:
                    mc.append([name])
                    for c in list(sorted(l)):
                        name = c["menu_name"] if c["menu_name"] else c["name"]
                        mc.append([" "+name, lambda x=c: self.task_menu(x)])
            return mc
        Menu([], self.i, self.o, contents_hook=get_task_menu_c, name="TaskManager main menu").activate()
