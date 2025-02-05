from PIL import ImageOps, Image

def splash(i, o):
    if (o.width, o.height) == (128, 64):
        image = Image.open("splash.png").convert('L')
        image = ImageOps.invert(image)
    elif o.width >= 128 and o.height >= 64:
        image = Image.open("splash_big.png").convert('L')
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
    image = image.convert(o.device_mode)
    o.display_image(image)


