# import the necessary packages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import base64
from PIL import Image
from StringIO import StringIO
import numpy as np
import urllib
import json
import cv2
import os
import random


# define the path to the face detector
FACE_DETECTOR_PATH = "{base_path}/cascades/haarcascade_frontalface_default.xml".format(
	base_path=os.path.abspath(os.path.dirname(__file__)))

SMILE_DETECTOR_PATH = "{base_path}/cascades/haarcascade_smile.xml".format(
	base_path=os.path.abspath(os.path.dirname(__file__)))

TRAINED_FACES_PATH = "{base_path}/yalefaces".format(
	base_path=os.path.abspath(os.path.dirname(__file__)))

# create the cascade classifiers
detector = cv2.CascadeClassifier(FACE_DETECTOR_PATH)
smiledetector = cv2.CascadeClassifier(SMILE_DETECTOR_PATH)

def get_images_and_labels(path):
    # Append all the absolute image paths in a list image_paths
    # We will not read the image with the .sad extension in the training set
    # Rather, we will use them to test our accuracy of the training
    image_paths = [os.path.join(path, f) for f in os.listdir(path) if not f.endswith('.DS_Store')]
    # images will contains face images
    images = []
    # labels will contains the label that is assigned to the image
    labels = []
    for image_path in image_paths:
        # Read the image and convert to grayscale
        image_pil = Image.open(image_path).convert('L')
        # Convert the image format into numpy array
        image = np.array(image_pil, 'uint8')
        # Get the label of the image
        nbr = int(os.path.split(image_path)[1].split(".")[0].replace("subject", ""))
        # Detect the face in the image
        faces = detector.detectMultiScale(image)
        # If face is detected, append the face to images and the label to labels
        for (x, y, w, h) in faces:
            images.append(image[y: y + h, x: x + w])
            labels.append(nbr)
            cv2.imshow("Adding faces to traning set...", image[y: y + h, x: x + w])
            #cv2.waitKey(50)
    # return the images list and labels list
    return images, labels

recognizer = cv2.face.createLBPHFaceRecognizer()
images, labels = get_images_and_labels(TRAINED_FACES_PATH)
recognizer.train(images, np.array(labels))

@csrf_exempt
def detect(request):
	# initialize the data dictionary to be returned by the request
	data = {}
	# check to see if this is a post request
	if request.method == "POST":
		# check to see if an image was uploaded
		if request.POST.get("imageBase64", None) is not None:
			# grab the uploaded image
			image = _grab_image(base64_string=request.POST.get("imageBase64", None))

		# otherwise, assume that a URL was passed in
		else:
			# grab the URL from the request
			url = request.POST.get("url", None)

			# if the URL is None, then return an error
			if url is None:
				data["error"] = "No URL provided."
				return JsonResponse(data)

			# load the image and convert
			image = _grab_image(url=url)

		# convert the image to grayscale, load the face cascade detector,
		# and detect faces in the image
		image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		rects = detector.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5,
			minSize=(30, 30), flags=0)

		# construct a list of bounding boxes from the detection
		rects = [(int(x), int(y), int(x + w), int(y + h)) for (x, y, w, h) in rects]
		if len(rects) == 0:
			data.update({"detected": False})
		else :
			x, y, w, h = rects[0]
			recognizer.setThreshold(40.0)
			identity = recognizer.predict(
				image[y:h, x:w]
				)
			#cv2.imwrite( TRAINED_FACES_PATH + "/" +  str(random.randint(1, 10)) + ".jpg", image[y:h, x:w] );
			smile = smiledetector.detectMultiScale(
			image[y:h, x:w],
			scaleFactor= 1.7,
			minNeighbors=22,
			minSize=(25, 25), 
			flags=0)
			smiling = False if len(smile) == 0 else True
			# update the data dictionary with the faces detected
			data.update({"detected": True, "identity": identity, "box": rects, "smiling": smiling})

	# return a JSON response
	return JsonResponse(data)

def _grab_image(path=None, base64_string=None, url=None):
	# if the path is not None, then load the image from disk
	if path is not None:
		image = cv2.imread(path)

	# otherwise, the image does not reside on disk
	else:	
		# if the URL is not None, then download the image
		if url is not None:
			resp = urllib.urlopen(url)
			data = resp.read()
			image = np.asarray(bytearray(data), dtype="uint8")
			image = cv2.imdecode(image, cv2.IMREAD_COLOR)

		# if the stream is not None, then the image has been uploaded
		elif base64_string is not None:
			# sbuf = StringIO()
			# sbuf.write(base64.b64decode(base64_string))
			# pimg = Image.open(sbuf)
			# image = cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)

			image = base64.b64decode(base64_string)
			image = np.fromstring(image, dtype=np.uint8)
			image = cv2.imdecode(image, 1)



		# convert the image to a NumPy array and then read it into
		# OpenCV format
 
	# return the image
	return image
