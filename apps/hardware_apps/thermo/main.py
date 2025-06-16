menu_name = "MLX90614" 

from mlx90614 import MLX90614

from zpui_lib.ui import Refresher

sensor = MLX90614()

def show_temp():
    try:
        amb_temp = round(sensor.read_amb_temp(), 1)
        obj_temp = round(sensor.read_obj_temp(), 1)
    except IOError:
        amb_temp = None
        obj_temp = None
    data = [
    "Ambient:"+str(amb_temp).rjust(o.cols-len("Ambient:")),
    "Object:"+str(obj_temp).rjust(o.cols-len("Object:"))]
    return data

#Callback global for ZPUI. It gets called when application is activated in the main menu

#Some globals for us
i = None #Input device
o = None #Output device

def callback():
    Refresher(show_temp, i, o, 0.1, name="Temperature monitor").activate()
