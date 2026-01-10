"""
core of the script taken from stackoverflow
"""
from datetime import datetime
from random import randint
import cv2
import sys
import os

fops = 30
period = 1/fops

image_folder = "screenshots/"
screenshot_time_format = "%y%m%d-%H%M%S:%f"
recording_time_format = "%y%m%d-%H%M%S"

if __name__ == "__main__":
    filename = sys.argv[1]
    with open(filename, 'r') as f:
        c = f.read()

    files = [c.strip() for c in c.split("\n")]
    files = list(filter(None, files))
    filtered_files = []
    for path in files:
        if path.startswith(image_folder):
            path = path[len(image_folder):]
            filtered_files.append(path)

    files = filtered_files

    file_ts_str = filename[len("recording-"):][:-1*len(".log")]
    file_ts = datetime.strptime(file_ts_str, recording_time_format)

    prev_ts = file_ts

    video_name = f'{filename}.avi'
    print(video_name)

    # read the first image to see which resolution it has

    print(os.path.join(image_folder, files[0]))
    #frame = cv2.imread(os.path.join(image_folder, files[0]))
    frame = cv2.imread(files[0])
    height, width, layers = frame.shape

    video = cv2.VideoWriter(video_name, 0, fops, (width,height))

    # now, load the remaining images

    for i, name in enumerate(files):
        ts_str = name[len("screenshot_"):][:-1*len(".png")]
        ts = datetime.strptime(ts_str, screenshot_time_format)
        frame_time = (ts-prev_ts).microseconds/1000_000
        #breakpoint()
        frame_count = int(frame_time//period)
        """# sometimes the frame time will be too short. let's uhhh flip a coin so as to whether include it =D
        if frame_count == 0: frame_count = random.randint(0,1)"""
        # let's simply use the filename index to decide whether to include a too-short frame
        if frame_count == 0: frame_count = i % 2
        if frame_count:
            print(f"Including path {name} for {frame_count} frames")
        else:
            print(f"Not including path {name}")
        for i in range(frame_count):
            video.write(cv2.imread(name))
        prev_ts = ts
        #breakpoint()


    video.release()
    #cv2.destroyAllWindows() # it just crashed without any benefit lol
