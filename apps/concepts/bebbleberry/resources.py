from noti_q.noti_q import NotificationQueue

from PIL import Image

from zpui_lib.helpers import local_path_gen

local_path = local_path_gen(__name__)

class ResourceManager:
    def __init__(self, c):
        self.s_width = 400
        self.s_height = 240

        self.noti_q = NotificationQueue()
        #self.MukataBold = c.load_font(local_path("res/fonts/Mukta-Bold.ttf"))
        #self.MukataSemiBold = c.load_font(local_path("res/fonts/Mukta-SemiBold.ttf"))
        #self.MukataRegular = c.load_font(local_path("res/fonts/Mukta-Regular.ttf"))
        self.MukataBold = local_path("res/fonts/Mukta-Bold.ttf")
        self.MukataSemiBold = local_path("res/fonts/Mukta-SemiBold.ttf")
        self.MukataRegular = local_path("res/fonts/Mukta-Regular.ttf")

        self.bell = Image.open(local_path("res/icons/bell-solid.png"))
        self.wifi = Image.open(local_path("res/icons/wifi-solid.png"))
        self.bluetooth = Image.open(local_path("res/icons/bluetooth-brands.png"))
        self.battery_level = [
            Image.open(local_path("res/icons/battery-empty-solid.png")),
            Image.open(local_path("res/icons/battery-quarter-solid.png")),
            Image.open(local_path("res/icons/battery-half-solid.png")),
            Image.open(local_path("res/icons/battery-full-solid.png"))
        ]
