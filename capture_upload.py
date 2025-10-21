import argparse
import json
import subprocess
import io
import logging
import os
import time
import shlex
from pathlib import Path
from subprocess import Popen, PIPE
from time import sleep
import cv2
import requests
from gpiozero import LED  # type: ignore
from picamera2 import Picamera2, MappedArray  # type: ignore
from datetime import datetime,timedelta
from PIL import Image
import socket
from roboflow import Roboflow
from ultralytics import YOLO
from ultralytics import settings

filepath = "/home/yuyang/picam"
predictpath = "/home/yuyang/predict/detect/predict"
hostname = socket.gethostname()
#get hostname to define which host sent alarm
filenamePrefix = hostname
diskSpaceToReserve = 256 * 1024 * 1024 # Keep 40 mb free on disk
max_file_count = 10
#use imx477 config and open auto focus
cameraSettings = "--autofocus-mode auto --tuning-file /usr/share/libcamera/ipa/rpi/pisp/imx477_af.json " 
 
# settings of the photos to save
saveWidth   = 1600
saveHeight  = 1200
saveQuality = 100 # Set jpeg quality (0 to 100)

# Initialize the Roboflow object with your API key





logging.basicConfig(
    filename='script.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Get available disk space
def getFreeSpace():
    st = os.statvfs(filepath + "/")
    du = st.f_bavail * st.f_frsize
    return du

def manageFileCount(directory, max_count):
    """
    Deletes the oldest files in the directory until the file count is within the allowed limit.
    """
    # Get list of all files in the directory with their full paths
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".jpg")]

    # If file count exceeds the maximum limit
    if len(files) > max_count:
        # Sort files by modification time (oldest first)
        files.sort(key=os.path.getmtime)
        
        # Calculate how many files need to be deleted
        files_to_delete = len(files) - max_count
        
        # Delete the oldest files
        for i in range(files_to_delete):
            try:
                os.remove(files[i])
                print(f"Deleted {files[i]} to maintain file count limit.")
            except Exception as e:
                print(f"Error deleting file {files[i]}: {e}")


def keepDiskSpaceFree(bytesToReserve):
    manageFileCount(filepath, max_file_count)
    manageFileCount(predictpath, max_file_count)
    if (getFreeSpace() < bytesToReserve):
        for filename in sorted(os.listdir(filepath + "/")):
            if filename.startswith(filenamePrefix) and filename.endswith(".jpg"):
                os.remove(filepath + "/" + filename)
                print ("Deleted %s/%s to avoid filling disk" % (filepath,filename))
                if (getFreeSpace() > bytesToReserve):
                    return
                

def saveImage(settings, width, height, quality, diskSpaceToReserve):
    keepDiskSpaceFree(diskSpaceToReserve)
    time = datetime.now()
    filenameSuffix = filenamePrefix + "-%04d%02d%02d-%02d%02d%02d" % (time.year, time.month, time.day, time.hour, time.minute, time.second)
    filename = filepath + "/" + filenameSuffix + ".jpg"
    subprocess.call("rpicam-still %s --width %s --height %s -t 1000 -e jpg -q %s -n -o %s" % (settings, width, height, quality, filename), shell=True)
    print ("Captured %s" % filename)
    return filename, filenameSuffix

def uploadimage(filename):
    try:
        response = project.upload(filename)
        print(f"Uploaded {filename}, response: {response}")
    except Exception as e:
        logging.error(f"Failed to upload {filename}: {e}")

def predictImage(filename):
    settings.update({"runs_dir":"/home/yuyang/predict"})
    model = YOLO(r"/home/yuyang/Downloads/best.pt")
    # accepts all formats - image/dir/Path/URL/video/PIL/ndarray. 0 for webcam
    results = model.predict(source=filename, show=False,save_txt=True,save=True, project= "/home/yuyang/predict/detect", exist_ok= True) 
    # Display preds. Accepts all YOLO predict arguments
    #saving to runs\detect\predict\labels. txt format is:[class] [x_center] [y_center] [width] [height] [confidence]
    return results




while (True):
    takepicture=True
    upload=True
    Predict=False
    uploadPred=False
    if takepicture:
     try:
        captured_name, captured_nameSuffix = saveImage(cameraSettings, saveWidth, saveHeight, saveQuality, diskSpaceToReserve)
     except Exception as e:
        logging.error(f"Error capturing image: {e}")
    

    if upload:
        uploadimage(captured_name)
    
    if Predict:
        results = predictImage(captured_name)
