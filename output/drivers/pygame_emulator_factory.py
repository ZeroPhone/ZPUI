"""
factory for pygame emulator device
sets minimum attributes,
creates device
returns it to caller
"""

import luma.emulator.device

from helpers import setup_logger

# ignore PIL debug messages

logger = setup_logger(__name__)

def get_pygame_emulator_device(width=128, height=64):
    """
    Creates and returns pygame emulator device.
    Width and height must match the size of the splash screen
    or an execption will be thrown during initializion.
    """

    #these are the bare minimum attributes needed to construct the emulator
    emulator_attributes = {}
    emulator_attributes['display'] = 'pygame'
    #width and height are in pixels
    emulator_attributes['width'] = width
    emulator_attributes['height'] = height

    Device = getattr(luma.emulator.device, 'pygame')

    device = Device(**emulator_attributes)

    return device
