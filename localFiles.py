# python localFiles.py -i 192.168.0.12 -o 8000 -videofile.xxx

from processing.motion_detection import Detector
from imutils.video import VideoStream
from flask import Response, redirect, jsonify
from flask import Flask
from flask import render_template
import threading
import argparse
import datetime
import imutils
import time
import numpy as np
import cv2
import time
import os
from flask import stream_with_context, request, Response, url_for
import base64

workingOn = True

outputFrame = None
resized = None
value = 0
running = False
progress = 0
fps = 0

lock = threading.Lock()
A = 0

app = Flask(__name__, static_url_path='/static')

streamList= [
	"videoplayback.mp4"
	]

# Working adresses:
# http://94.72.19.58/mjpg/video.mjpg,
# http://91.209.234.195/mjpg/video.mjpg
# http://209.194.208.53/mjpg/video.mjpg
# http://66.57.117.166:8000/mjpg/video.mjpg

frameList = []
bufferFrames = []
frameOutList = []
vsList = []
motionDetectors = []
grayFrames = []
total = []
classes = []

frameProcessed = 0
fileIterator = 0
totalFrames = 0

for i in range(len(streamList)):
	vsList.append(VideoStream(streamList[i]))
	frameList.append(None)
	bufferFrames.append(None)
	frameOutList.append(None)
	motionDetectors.append(None)
	grayFrames.append(None)
	#vsList[i].start()

net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

with open("coco.names", "r") as f:
	classes = [line.strip() for line in f.readlines()]

layers_names = net.getLayerNames()
outputLayers = [layers_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
colors = np.random.uniform(0,255,size=(len(classes), 3))
img = None

time.sleep(2.0)


fourcc = cv2.VideoWriter_fourcc(*"MJPG")
writer = None

def ProcessFrame(frameCount):
	global cap, totalFrames, progress, fps, resized, workingOn, vsList, writer, net, fileIterator, frameProcessed, outputFrame, lock

	workingOn = True

	fileToRender=args["source"]
	cap = cv2.VideoCapture(fileToRender)

	while True:
		# grab the current frame
		(grabbed, frame) = cap.read()

		if not grabbed:
			break

		totalFrames = totalFrames + 1

	cap = cv2.VideoCapture(fileToRender)

	while workingOn == True:
		classesIndex = []
		startMoment = time.time()
		for streamIndex in range(len(streamList)):
			ret, frameList[streamIndex] = cap.read()
			if frameList[streamIndex] is not None:
				bufferFrames[streamIndex] = frameList[streamIndex].copy()
				#frameList[streamIndex] = cv2.resize(frameList[streamIndex], (800,600))
				#bufferFrames[streamIndex] = cv2.resize(bufferFrames[streamIndex], (800,600))
				height, width, channels = frameList[streamIndex].shape

				blob = cv2.dnn.blobFromImage(frameList[streamIndex], 0.003, (640,640), (0, 0, 0), True, crop=False)
				net.setInput(blob)
				outs = net.forward(outputLayers)

				class_ids = []
				confidences = []
				boxes = []

				for out in outs:
					for detection in out:
						scores = detection[5:]
						class_id = np.argmax(scores)
						confidence = scores[class_id]
						if confidence > 0.5:
							w = int(detection[2] * width)
							h = int(detection[3] * height)
							center_x = int(detection[0] * width)
							center_y = int(detection[1] * height)
							x = int(center_x - w/2)
							y = int(center_y - h/2)
							boxes.append([x, y, w, h])
							confidences.append(float(confidence))
							class_ids.append(class_id)
							#cv2.rectangle(bufferFrames[streamIndex], (x, y), (x + w, y + h), (0,255,0), 2)

				indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.2)

				#print(indexes)
				print("=========================")
				font = cv2.FONT_HERSHEY_SIMPLEX
				lineType = cv2.LINE_AA

				classesOut = []
				objectIndex = 0

				for i in range(len(boxes)):
					if i in indexes:
						x, y, w, h = boxes[i]
						label = classes[class_ids[i]]
						color = colors[class_ids[i]]

						classesOut.append(class_ids[i])

						# if (x<0):
						# 	x = 0
						# if (y<0):
						# 	y=0
						# fileIterator += 1
						# #crop_img = frameList[streamIndex][y:y+h, x:x+w]
						# cv2.imwrite(label + str(fileIterator)+".jpg", crop_img)
						# #cv2.imshow("sf", crop_img)

						blk = np.zeros(bufferFrames[streamIndex].shape, np.uint8)

						if label == "person":
							cv2.putText(bufferFrames[streamIndex], label + "[" + str(np.round(confidences[i], 2)) + "]", (x, y - 5), font, 0.7, (0,255,0), 2, lineType = cv2.LINE_AA)
							cv2.rectangle(blk, (x, y), (x + w, y + h), (0,255,0), cv2.FILLED)
							bufferFrames[streamIndex] = cv2.addWeighted(bufferFrames[streamIndex], 1, blk, 0.2, 0)
						if label == "car":
							cv2.putText(bufferFrames[streamIndex], label + "[" + str(np.round(confidences[i], 2)) + "]", (x, y - 5), font, 0.7, (213,160,47), 2, lineType = cv2.LINE_AA)
							cv2.rectangle(blk, (x, y), (x + w, y + h), (213,160,47), cv2.FILLED)
							bufferFrames[streamIndex] = cv2.addWeighted(bufferFrames[streamIndex], 1, blk, 0.2, 0)
						if ((label != "car") & (label != "person")):
							cv2.putText(bufferFrames[streamIndex], label + "[" + str(np.round(confidences[i], 2)) + "]", (x, y - 5), font, 0.7, color, 2, lineType = cv2.LINE_AA)
							cv2.rectangle(blk, (x, y), (x + w, y + h), color, cv2.FILLED)
							bufferFrames[streamIndex] = cv2.addWeighted(bufferFrames[streamIndex], 1, blk, 0.2, 0)

						# 	cv2.putText(bufferFrames[streamIndex], label + "[" + str(np.round(confidences[i], 2)) + "]", (x, y - 5), font, 0.7, (0,255,0), 2, lineType = cv2.LINE_AA)
						# 	cv2.rectangle(blk, (x, y), (x + w, y + h), (0,255,0), cv2.FILLED)
						# 	bufferFrames[streamIndex] = cv2.addWeighted(bufferFrames[streamIndex], 1, blk, 0.2, 0)
						# if (label == "handbag")|(label == "backpack"):
						# 	cv2.circle(bufferFrames[streamIndex], (x+int(round(w/2)), y+int(round(h/2))), 3, (0, 0, 255), 3)
						# 	bufferFrames[streamIndex] = cv2.addWeighted(bufferFrames[streamIndex], 1, blk, 0.2, 0)

						cv2.rectangle(bufferFrames[streamIndex], (x, y), (x + w, y + h), (255,255,255), 2)
						#cv2.imshow('123', bufferFrames[streamIndex])
						#cv2.waitKey()
						objectIndex+=1

				classesIndex.append(classesOut)

				with lock:
					frameProcessed = frameProcessed + 1
					elapsedTime = time.time()
					fps = 1 / (elapsedTime - startMoment)
					print (fps)
					for streamIndex in range(len(streamList)):
						classIndexCount = [[0 for x in range(80)] for x in range(len(streamList))]
						countLocal = [0 for x in range(80)]
						skipFlag = False
						passFlag = False
						#cv2.rectangle(bufferFrames[streamIndex], (20, 30), (400, 86), (0, 0, 0), -1)
						#cv2.putText(bufferFrames[streamIndex], "BLOB: 320x320", (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2, lineType=cv2.LINE_AA)
						#cv2.rectangle(bufferFrames[streamIndex], (20, 100), (400, 156), (0, 0, 0), -1)
						#cv2.putText(bufferFrames[streamIndex], "FPS: " + str(round(fps, 2)), (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2, lineType=cv2.LINE_AA)

						rowIndex = 1
						for m in range(80):
							for k in range(len(classesIndex[streamIndex])):
								if (m == classesIndex[streamIndex][k]):
									classIndexCount[streamIndex][m]+=1

							if (classIndexCount[streamIndex][m]!=0):
								rowIndex += 1

								# cv2.rectangle(bufferFrames[streamIndex], (0, rowIndex*40 - 20), (200,rowIndex*40 + 8), (0,0,0), -1)
								# cv2.putText(bufferFrames[streamIndex], classes[m] + ": " + str(classIndexCount[streamIndex][m]), (20,rowIndex*40), font, 0.7, colors[m], 2, cv2.LINE_AA)

								if (classes[m]=="person"):
									cv2.rectangle(bufferFrames[streamIndex], (20, rowIndex * 70 - 40), (400,rowIndex * 70 + 16), (0,0,0), -1)
									cv2.putText(bufferFrames[streamIndex], classes[m] + ": " + str(classIndexCount[streamIndex][m]), (40, rowIndex * 70), font, 1.4, (0,255,0), 2, lineType=cv2.LINE_AA)
								if (classes[m]=="car"):
									cv2.rectangle(bufferFrames[streamIndex], (20, rowIndex * 70 - 40), (400, rowIndex * 70 + 16), (0, 0, 0), -1)
									cv2.putText(bufferFrames[streamIndex], classes[m] + ": " + str(classIndexCount[streamIndex][m]), (40, rowIndex * 70), font, 1.4, (213,160,47), 2, lineType=cv2.LINE_AA)
								if ((classes[m] != "car") & (classes[m] != "person")):
									cv2.rectangle(bufferFrames[streamIndex], (20, rowIndex * 70 - 40), (400, rowIndex * 70 + 16), (0, 0, 0), -1)
									cv2.putText(bufferFrames[streamIndex], classes[m] + ": " + str(classIndexCount[streamIndex][m]), (40, rowIndex * 70), font, 1.4, colors[m], 2, lineType=cv2.LINE_AA)

								if (classes[m]=="handbag")|(classes[m]=="backpack"):
									passFlag = True
									print("handbag detected! -> PASS")

						if writer is None:
							writer = cv2.VideoWriter(f"static/output{args['port']}.avi", fourcc, 30,(bufferFrames[streamIndex].shape[1], bufferFrames[streamIndex].shape[0]), True)
						else:
							resized = bufferFrames[streamIndex].copy()

							progress = frameProcessed / totalFrames * 100

							cv2.rectangle(resized, (20, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 80), (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) - 20, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 24), (0, 0, 0), -1)

							if (progress != "DONE"):
								cv2.rectangle(resized, (20, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 80), (int( cap.get(cv2.CAP_PROP_FRAME_WIDTH) * progress / 100) - 20, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 24), (0, 255, 0), -1)
								cv2.putText(resized, str(int(progress)) + "%" + " | FPS: " + str(round(fps,2)), (40, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 40), font, 1.4, (0, 0, 255), 2, lineType=cv2.LINE_AA)

							writer.write(bufferFrames[streamIndex])
							cv2.imwrite("static/t.jpg", bufferFrames[streamIndex])

							resized = cv2.resize(resized, (1280, 720))
							cv2.imshow("video", resized)
							key = cv2.waitKey(1) & 0xFF

					# if (skipFlag == False)&(passFlag==True):
					# 	writer.write(bufferFrames[streamIndex])
					# 	resized = cv2.resize(bufferFrames[streamIndex], (1280, 720))
					# 	cv2.imshow("video", resized)
					# 	key = cv2.waitKey(1) & 0xFF
					#im_v = cv2.vconcat([bufferFrames[0], bufferFrames[1]])
					#im_v2 = cv2.vconcat([bufferFrames[2], bufferFrames[3]])
					#im_v3 = cv2.hconcat([im_v, im_v2])
					#vis = np.concatenate((im_v, frameList[0]), axis=1)
					#outputFrame = im_v3.copy()
					#outputFrame = bufferFrames[streamIndex]
					outputFrame = resized

			else:
				#return redirect(f"http://192.168.0.12:{args['port']}/results.html")
				outputFrame = bufferFrames[streamIndex]
				workingOn = False
				print("finished")

def generate():
	global outputFrame, frameProcessed, lock, workingOn

	while workingOn:
		#if frameProcessed < 100:
		with lock:
			if outputFrame is None:
				continue

			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

			if not flag:
				continue

		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
			bytearray(encodedImage) + b'\r\n')
		#else:
			#return redirect(url_for("results"))
			#return redirect('/results')

@app.route('/')
@app.route('/<device>/<action>')

def index(device=None, action=None):

	return render_template("index.html", frameProcessed=frameProcessed, pathToRenderedFile=f"static/output{args['port']}.avi")

@app.route("/video")

def video_feed():
	#redirect(f"http://192.168.0.12:8000/results")
	return Response(generate(),
		mimetype="multipart/x-mixed-replace; boundary=frame")
		#return Response(stream_with_context(generate()))

@app.route("/results")

def results():
	return render_template("results.html")

@app.route('/update', methods=['POST'])
def update():
	return jsonify({
		'value': frameProcessed,
		'totalFrames': totalFrames,
		'progress': round(progress, 2),
		'fps': round(fps, 2),
		#'time': datetime.datetime.now().strftime("%H:%M:%S"),
	})

# check to see if this is the main thread of execution
if __name__ == '__main__':
	ap = argparse.ArgumentParser()
	ap.add_argument("-i", "--ip", type=str, required=True,
		help="ip address of the device")
	ap.add_argument("-o", "--port", type=int, required=True,
		help="ephemeral port number of the server (1024 to 65535)")
	ap.add_argument("-s", "--source", type=str, default=32,
		help="# file to render")
	ap.add_argument("-f", "--frame-count", type=int, default=32,
		help="# of frames used to construct the background model")

	args = vars(ap.parse_args())

	t = threading.Thread(target=ProcessFrame, args=(
		args["frame_count"],))
	t.daemon = True
	t.start()

	app.run(host=args["ip"], port=args["port"], debug=False,
		threaded=True, use_reloader=False)

for j in range(len(streamList)):
	vsList[j].stop()
