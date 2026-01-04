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

    module_path = '/sys/module/'
    sharp_path = module_path+"sharp_drm/"
    driver_path = None # might end up == sharp_drm, might end up as a jdi_* path instead if a jdi driver of some sorts is used
    mc_add = "parameters/mono_cutoff"
    cc_add = "parameters/color_cutoff"
    mc_path = sharp_path+mc_add # will be changed if some jdi_ driver is used
    cc_path = None # colorberry-specific, some sort of JDI driver is assumed
    name_path = "/sys/class/graphics/fb{}/name"
    # original mc and cc storage
    orig_mc = None
    orig_cc = None

    def __init__(self, fb_num=1, mono_cutoff=128, color_cutoff=64, force_color=False, **kwargs):
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
        self.color_cutoff = color_cutoff
        try:
            self.try_find_store_and_replace_mc()
            self.try_find_store_and_replace_cc()
        except:
            logger.exception("Error while setting new mono/color thresholds!")

    def is_sharp_memory(self, fb_path):
        # fb_path unused for now - right now, we only check that sharp_drm driver is loaded
        # sorry if this gives you trouble =(
        return os.path.exists(self.sharp_path)

    def try_find_store_and_replace_mc(self):
        """Stores and replaces sharp_drm/JDI driver mono cutoff"""
        # check if the parameter is available at all  - maybe sharp_drm is not used?
        dir = None
        if os.path.exists(self.mc_path):
            dir = self.sharp_path
        else: # look for jdi
            for name in os.listdir(self.module_path):
                if name.startswith("jdi_"):
                    dir = os.path.join(self.module_path, name)
                    break
        if dir == None:
            return
        # we got a directory!
        self.mc_path = os.path.join(dir, self.mc_add)
        logger.info("Found directory for setting parameters: {}, mono_cutoff path: {}".format(dir, self.mc_path))
        self.driver_path = dir
        if os.path.exists(self.mc_path):
            with open(self.mc_path, 'rb') as f:
               self.orig_mc = f.read().strip()
            mc_bytes = bytes(str(self.mono_cutoff), "ascii")
            logger.info("replacing the original mono cutoff {} with {}".format( repr(self.orig_mc), repr(mc_bytes) ))
            with open(self.mc_path, 'wb') as f:
               f.write(mc_bytes)

    def try_find_store_and_replace_cc(self):
        """Stores and replaces JDI driver color cutoff"""
        # assumes that self.driver_path has been successfully set
        if self.driver_path:
            cc_path = os.path.join(self.driver_path, self.cc_add)
            if os.path.exists(cc_path):
                self.cc_path = cc_path
                with open(self.cc_path, 'rb') as f:
                   self.orig_cc = f.read().strip()
                cc_bytes = bytes(str(self.color_cutoff), "ascii")
                logger.info("replacing the original color cutoff {} with {}".format( repr(self.orig_cc), repr(cc_bytes) ))
                with open(self.cc_path, 'wb') as f:
                    f.write(cc_bytes)

    def atexit(self):
        FBScreen.atexit(self)
        try:
            if self.orig_mc != None:
                with open(self.mc_path, 'wb') as f:
                    f.write(self.orig_mc)
        except:
            logger.exception("Failed to re-set the original mono cutoff!")
        try:
            if self.orig_cc != None:
                with open(self.cc_path, 'wb') as f:
                    f.write(self.orig_mc)
        except:
            logger.exception("Failed to re-set the original color cutoff!")
