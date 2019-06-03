from canvas import Canvas

"""
Zone requirements:
- get values from some kind of source
- get new images from an image-generating callback
- only get a new image when the value changes
- keep the current image in memory
- optionally, cache the images for the values
"""

class Zone(object):
    """
    Allows us to avoid re-generating icons/graphics for different values,
    i.e. if we need to draw a clock, we can use zones to avoid redrawing
    the hours/minutes too often and save some CPU time. Also implements
    caching, so after some time we won't need to redraw, say, seconds -
    just getting the cached image for each of the 60 possible values.
    """
    value = None
    image = None
    prev_value = None
    cache = {}

    def __init__(self, value_cb, image_cb, caching = True, i_pass_self = False, v_pass_self = False):
        self.value_cb = value_cb
        self.image_cb = image_cb
        self.caching = caching
        self.v_pass_self = v_pass_self
        self.i_pass_self = i_pass_self
        if self.caching:
            self.cache = {}

    def needs_refresh(self):
        # Getting new value
        if self.v_pass_self:
            new_value = self.value_cb(self)
        else:
            new_value = self.value_cb()
        if new_value != self.value:
            # New value!
            self.prev_value = self.value
            self.value = new_value
            return True
        return False

    def update_image(self):
        # Checking the cache
        if self.caching:
            if self.value in self.cache:
                return self.cache[self.value]
        # Not caching or not found - generating
        if self.i_pass_self:
            image = self.image_cb(self.value, self)
        else:
            image = self.image_cb(self.value)
        # If caching, storing
        if self.caching:
            self.cache[self.value] = image
        return image

    def get_image(self):
        return self.image

    def refresh(self):
        if self.needs_refresh():
            self.image = self.update_image()


class ZoneManager(object):

    def __init__(self, zones):
        self.zones = zones

    def refresh(self):
        for zone in self.zones.values():
            zone.refresh()



markup = [
  ("gsm", "...", "battery"),
  ("..."),
  ("time_hm", "time_s"),
  ("..."),
  ("...", "b1", "...", "b2", "...")
]
