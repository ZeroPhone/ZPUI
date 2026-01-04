#!/usr/bin/python

# luma.core library used: https://github.com/rm-hull/luma.core

import os
import traceback
from mock import Mock
from threading import Lock

from luma.core.render import canvas
from PIL import ImageChops, Image

import atexit

from zpui_lib.helpers import setup_logger
logger = setup_logger(__name__, "info")

try:
    from ..output import GraphicalOutputDevice, CharacterOutputDevice
except ModuleNotFoundError:
    from output import GraphicalOutputDevice, CharacterOutputDevice

from output.drivers.fb import Screen as FBScreen

function_mock = lambda *a, **k: True


class Screen(FBScreen):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    sharp_path = '/sys/module/sharp_drm/'
    mc_path = sharp_path+"parameters/mono_cutoff"
    name_path = "/sys/class/graphics/fb{}/name"
    orig_mc = None

    def __init__(self, fb_num=1, mono_cutoff=128, force_color=False, **kwargs):
        self.force_color = force_color
        color = True # true for all devices but a few
        try:
            with open(self.name_path.format(fb_num)) as f:
                name = f.read().strip()
        except:
            logger.exception("error when reading fb device driver name!")
        else:
            if name.startswith("sharp_drm"):
                if force_color:
                    logger.info("Sharp_drm driver detecting but color forced to True (Colorberry?)")
                else:
                    color = False
                    logger.info("Sharp_drm driver detecting, changing driver to monochrome")
        kwargs["fb_num"] = fb_num # need to pass it to FBScreen constructor too
        FBScreen.__init__(self, color=color, **kwargs)
        self.mono_cutoff = mono_cutoff
        self.try_store_and_replace_mc()

    def is_sharp_memory(self, fb_path):
        # fb_path unused for now - right now, we only check that sharp_drm driver is loaded
        # sorry if this gives you trouble =(
        return os.path.exists(self.sharp_path)

    def try_store_and_replace_mc(self):
        """Stores and replaces beepy kbd driver touch threshold"""
        # check if the parameter is available at all  - maybe sharp_drm is not used?
        if os.path.exists(self.mc_path):
            with open(self.mc_path, 'rb') as f:
               self.orig_mc = f.read().strip()
            mc_bytes = bytes(str(self.mono_cutoff), "ascii")
            logger.info("replacing the original sharp_drm mono cutoff {} with {}".format( repr(self.orig_mc), repr(mc_bytes) ))
            with open(self.mc_path, 'wb') as f:
               f.write(mc_bytes)

    def atexit(self):
        FBScreen.atexit(self)
        try:
            if self.orig_mc != None:
                with open(self.mc_path, 'wb') as f:
                    f.write(self.orig_mc)
        except:
            logger.exception("Failed to re-set the original mono cutoff!")
