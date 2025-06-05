from PIL import ImageOps, Image, ImageColor

def replace_color(icon, fromc, toc):
    import numpy as np
    icon = icon.convert("RGBA")
    # from https://stackoverflow.com/questions/3752476/python-pil-replace-a-single-rgba-color
    if isinstance(fromc, str):
        fromc = ImageColor.getrgb(fromc)
    data = np.array(icon)
    r, g, b, a = data.T
    areas = (r == fromc[0]) & (g == fromc[1]) & (b == fromc[2])
    if isinstance(toc, str):
        toc = ImageColor.getrgb(toc)
    data[..., :-1][areas.T] = toc
    return Image.fromarray(data)

def splash(i, o, color="white"):
    if (o.width, o.height) == (128, 64):
        image = Image.open("resources/splash.png").convert('1')
        image = ImageOps.invert(image)
    elif o.width >= 128 and o.height >= 64:
        image = Image.open("resources/splash_big.png").convert('1')
        image = ImageOps.invert(image)
        size = o.width, o.height
        image.thumbnail(size, Image.ANTIALIAS)
        left = top = right = bottom = 0
        width, height = image.size
        if o.width > width:
            delta = o.width - width
            left = delta // 2
            right = delta - left
        if o.height > height:
            delta = o.height - height
            top = delta // 2
            bottom = delta - top
        image = ImageOps.expand(image, border=(left, top, right, bottom), fill="black")
    else:
        o.display_data("Welcome to", "ZPUI")
        return
    if color != "white":
        image = replace_color(image, "white", color)
    image = image.convert(o.device_mode)
    o.display_image(image)


