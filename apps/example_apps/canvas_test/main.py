menu_name = "Canvas test"

from ui import Canvas

# this is a funny fps test, in particular, useful for emulator testing

def callback():
    # needs a color display
    if "color" not in o.type:
        print("so no color? o..o")
        return
    canvas_1 = Canvas(o)
    canvas_2 = Canvas(o)
    cx, cy = canvas_1.get_center()
    # canvas 1
    i1 = o.width // 5
    canvas_1.clear(fill="cyan")
    canvas_1.rectangle((i1, 0, str(-1*i1), o.height-1), fill="pink", outline="pink")
    canvas_1.rectangle((cx-i1//2, 0, cx+i1//2, o.height-1), fill="white")
    i2 = o.height // 5
    canvas_2.clear(fill="cyan")
    canvas_2.rectangle((0, i2, o.width-1, str(-1*i2)), fill="pink", outline="pink")
    canvas_2.rectangle((0, cy-i2//2, o.width-1, cy+i2//2), fill="white")
    while True:
        canvas_1.display()
        canvas_2.display()
