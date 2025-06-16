menu_name = "Python sandbox"

from zpui_lib.ui import Canvas

i = None
o = None
c = None
context = None

def init_app(input, output):
    global i, o, c
    i = input; o = output
    c = Canvas(o, interactive=True)

def set_context(new_context):
    global context
    context = new_context

def callback():
    import code as __code__
    c.display()
    # Making sure that Ctrl+C is caught and doesn't cause the driver to crash...
    # Well, doesn't really work
    exit = False
    while not exit:
        try:
            __code__.interact(local=dict(globals(), **locals()))
        except KeyboardInterrupt:
            pass
        else:
             exit = True
             raise
