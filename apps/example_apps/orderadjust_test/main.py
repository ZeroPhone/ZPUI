from zpui_lib.helpers import setup_logger
from zpui_lib.ui import OrderAdjust

menu_name = "OrderAdjust test" # App name as seen in main menu while using the system

logger = setup_logger(__name__, "info")
# Some globals for us
i = None # Input device
o = None # Output device

def callback():
    listbox_contents = [
    ["2"],
    ["1"],
    ["3"],
    ["6"],
    ["4"]]
    logger.info(OrderAdjust(listbox_contents, i, o).activate())
