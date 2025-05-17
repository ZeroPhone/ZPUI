"""
core of the script taken from stackoverflow
"""

import cv2
import os

image_folder = '.'
video_name = 'compilation.avi'

if __name__ == "__main__":
    images = list(sorted([img for img in os.listdir(image_folder) if img.endswith(".png")]))
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    video = cv2.VideoWriter(video_name, 0, 30, (width,height))

    for image in images:
        video.write(cv2.imread(os.path.join(image_folder, image)))

    #cv2.destroyAllWindows() # it just crashed without any benefit lol
    video.release()
