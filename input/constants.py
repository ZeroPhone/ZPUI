from enum import Enum


class KeyCodes(Enum):
    KEY_LEFT = "KEY_LEFT"
    KEY_UP = "KEY_UP"
    KEY_DOWN = "KEY_DOWN"
    KEY_RIGHT = "KEY_RIGHT"
    KEY_ENTER = "KEY_ENTER"
    KEY_1 = "KEY_1"
    KEY_2 = "KEY_2"
    KEY_3 = "KEY_3"
    KEY_4 = "KEY_4"
    KEY_5 = "KEY_5"
    KEY_6 = "KEY_6"
    KEY_7 = "KEY_7"
    KEY_8 = "KEY_8"
    KEY_9 = "KEY_9"
    KEY_STAR = "KEY_*"
    KEY_0 = "KEY_0"
    KEY_SHARP = "KEY_#"
    KEY_F1 = "KEY_F1"
    KEY_F2 = "KEY_F2"
    KEY_ANSWER = "KEY_ANSWER"
    KEY_HANGUP = "KEY_HANGUP"
    KEY_PAGEUP = "KEY_PAGEUP"
    KEY_PAGEDOWN = "KEY_PAGEDOWN"
    KEY_F5 = "KEY_F5"
    KEY_F6 = "KEY_F6"
    KEY_VOLUMEUP = "KEY_VOLUMEUP"
    KEY_VOLUMEDOWN = "KEY_VOLUMEDOWN"
    KEY_PROG1 = "KEY_PROG1"
    KEY_PROG2 = "KEY_PROG2"
    KEY_CAMERA = "KEY_CAMERA"

    # todo: discuss aliases
    # todo: discuss usefulness
    def confirm(self, key_code):
        return key_code in [self.KEY_ANSWER, self.KEY_RIGHT, self.KEY_F1]

    def cancel(self, key_code):
        return key_code in [self.KEY_HANGUP, self.KEY_LEFT, self.KEY_F2]
