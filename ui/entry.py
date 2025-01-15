from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")

class Entry(object):
    text = None
    name = None
    icon = None
    state = None
    cb = None
    cb2	 = None
    audio_text = None

    def __init__(self, text, cb=None, cb2=None, icon=None, name=None, audio_text = None, state=None, **kwargs):
        self.text = text
        self.cb = cb
        self.cb2 = cb2
        self.icon = icon
        self.name = name
        self.state = state
        self.audio_text = audio_text if audio_text else text
        for k, v in kwargs.items():
            setattr(self, k, v)
