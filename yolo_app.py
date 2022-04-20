#!/usr/bin/python3

"""
Flask WebApp to access and control Raspberry Pi Rover with YOLO object detection.

Author: Yash Indane
Email: yashindane46@gmail.com
"""

import cv2
import time
import argparse
import numpy as np
from subprocess import getoutput
from flask import Flask, Response, render_template, request


#Weigths and config for all models at https://pjreddie.com/darknet/yolo/

#The arguments are optional.
ap = argparse.ArgumentParser()

ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
ap.add_argument("-t", "--threshold", type=float, default=0.3,
	help="threshold when applyong non-maxima suppression")
args = vars(ap.parse_args())

labelsPath = "coco.names"
LABELS = open(labelsPath).read().strip().split("\n")
#Initialize a list of colors to represent each possible class label
np.random.seed(42)
COLORS = np.random.randint(0, 255, size=(len(LABELS), 3), dtype="uint8")
#Derive the paths to the YOLO weights and model configuration
weightsPath = "yolov3-tiny.weights"
configPath = "yolov3tiny.cfg"
#Load our YOLO object detector trained on COCO dataset (80 classes) and determine only the *output* layer names that we need from YOLO
print("[INFO] loading YOLO from disk...")
net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)
ln = net.getLayerNames()
ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

app = Flask("Raspberry Pi Rover")

#Open system Camera
cap = cv2.VideoCapture(0)

#For IP Webcam
#address = "https://<IP>:8080/video"
#cap.open(address)

#Counter for saving snaps
i = 0

#Flag to start pedestrian detection
detection_enable = False


#Changing value of detection flag
@app.route("/detection", methods=["GET"])
def enable_detection():
    global detection_enable
    if request.args.get("value") == "true":
        detection_enable = True
    else:
        detection_enable = False
    return "0"


#Detects Objects in frame using YOLO V3-Tiny
def object_detection(frame):
        (H, W) = frame.shape[:2]

        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        start = time.time()
        layerOutputs = net.forward(ln)
        end = time.time()

        boxes = []
        confidences = []
        classIDs = []

        #Loop over each of the layer outputs
        for output in layerOutputs:
                #Loop over each of the detections
                for detection in output:
                        #Extract the class ID and confidence (i.e., probability) of the current object detection
                        scores = detection[5:]
                        classID = np.argmax(scores)
                        confidence = scores[classID]
                        #Filter out weak predictions by ensuring the detected probability is greater than the minimum probability
                        if confidence > args["confidence"]:
                                #Scale the bounding box coordinates back relative to the size of the image
                                box = detection[0:4] * np.array([W, H, W, H])
                                (centerX, centerY, width, height) = box.astype("int")
                                #Use the center (x, y)-coordinates to derive the top and and left corner of the bounding box
                                x = int(centerX - (width / 2))
                                y = int(centerY - (height / 2))
                                #Update our list of bounding box coordinates, confidences, and class IDs
                                boxes.append([x, y, int(width), int(height)])
                                confidences.append(float(confidence))
                                classIDs.append(classID)

        #Apply non-maxima suppression to suppress weak, overlapping bounding boxes
        idxs = cv2.dnn.NMSBoxes(boxes, confidences, args["confidence"],
                args["threshold"])
        #Ensure at least one detection exists
        if len(idxs) > 0:
                #Loop over the indexes we are keeping
                for i in idxs.flatten():
                        #Extract the bounding box coordinates
                        (x, y) = (boxes[i][0], boxes[i][1])
                        (w, h) = (boxes[i][2], boxes[i][3])
                        #Draw a bounding box rectangle and label on the frame
                        color = [int(c) for c in COLORS[classIDs[i]]]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        text = "{}: {:.4f}".format(LABELS[classIDs[i]],
                                confidences[i])
                        cv2.putText(frame, text, (x, y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return frame


#Generating frames from stream
def gen():
    global final_frame
    prev_timestamp = 0
    while True:
        ret, frame = cap.read()
        initial_timestamp = time.time()
        #Processing frames
        try:
          scale_percent = 80
          width = int(frame.shape[1] * scale_percent/100)
          height = int(frame.shape[0] * scale_percent/100)
          dim = (width, height)
          frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
          if detection_enable:
              frame = object_detection(frame)
          FPS = "FPS " + str(int(1/(initial_timestamp-prev_timestamp)))
          prev_timestamp = initial_timestamp
          cv2.putText(frame, FPS, (7, 36), cv2.FONT_HERSHEY_SIMPLEX, 1, (100,255,0), 2,  cv2.LINE_AA)
          ret, png = cv2.imencode(".png", frame)
          final_frame = frame
          frame = png.tobytes()
          yield(b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n\r\n')
        except Exception as e:
            print(e)


#For taking snaps
@app.route("/snap")
def snap():
    global i
    i += 1
    path = f"./snaps/image{str(i)}.png"
    cv2.imwrite(path, final_frame)
    return "0"


#For running commands
@app.route("/command", methods=["GET"])
def run_command():
    cmd = request.args.get("cmd")
    #Run the command
    command_status = getoutput(f"sudo {cmd}")
    return command_status


#This route is just streaming frames at a endpoint
#To use at other route <img src="http://<IP>:5500/stream" />
@app.route("/stream")
def stream():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


#Homepage
@app.route("/rover")
def rover():
    return render_template("home.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5500")
