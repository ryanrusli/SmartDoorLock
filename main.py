import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

import os
import time
import RPi.GPIO as GPIO
from picamera import PiCamera

import pyttsx3
import playsound
import speech_recognition as sr
from gtts import gTTS

import csv
import boto3
import json

from aws_rds_python import *

#def speak(text):
#    tts = gTTS(text=text, lang='en')
#    filename = 'voice.mp3'
#    tts.save(filename)
#    playsound.playsound(filename)

def SendMail(ImgFileName):
    img_data = open(ImgFileName, 'rb').read()
    msg = MIMEMultipart()
    msg['Subject'] = 'Unknown Person Detected'
    msg['From'] = 'sender@email.com'
    msg['To'] = 'receiever@email.com'

    text = MIMEText("Your smart door lock detected an unknown individual.")
    msg.attach(text)
    image = MIMEImage(img_data, name=os.path.basename(ImgFileName))
    msg.attach(image)

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login("sender@email.com", "password")
    s.sendmail("sender@email.com", 'receiver@email.com',  msg.as_string())
    s.quit()

with open('/home/pi/Desktop/my_user_credentials.csv', 'r') as input:
    next(input)
    reader = csv.reader(input)
    for line in reader:
        access_key_id = line[2]
        secret_access_key = line[3]

camera = PiCamera()

relay = 18;
infrared = 23;
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay, GPIO.OUT)
GPIO.setup(infrared, GPIO.IN)
GPIO.output(relay, 1)

while True:
    while GPIO.input(infrared) == True:
        print("Nothing detected")

    print("Object Detected")
    camera.start_preview()
    time.sleep(2)
    camera.capture('/home/pi/Desktop/livecapture.jpg')
    camera.stop_preview()
    photo = '/home/pi/Desktop/livecapture.jpg'
    s3_client = boto3.client('s3',
                             aws_access_key_id=access_key_id,
                             aws_secret_access_key=secret_access_key)
    s3_client.upload_file(photo, 'face-comparison-data', 'live-capture')



    client = boto3.client('rekognition',
                          region_name='ap-southeast-1',
                          aws_access_key_id=access_key_id,
                          aws_secret_access_key=secret_access_key)



    response = client.compare_faces(
            SourceImage={
                'S3Object': {
                    'Bucket': 'face-comparison-data',
                    'Name': 'live-capture'
                }
            },
            TargetImage={
                'S3Object': {
                    'Bucket': 'face-comparison-data',
                    'Name': 'ryan2.jpg'
                }
            },
    )


    #with open(photo, 'rb') as source_image:
    #    source_bytes = source_image.read()
    #
    #response = client.detect_labels(Image={'Bytes': source_bytes},
    #                                MaxLabels=10
    #                                )

    #print(response['FaceMatches'])

    match = False
    for key, value in response.items():
        if key == 'FaceMatches' and value != '' and value != []:
            if(value[0]['Similarity'] > 95):
                match = True
    #        print(key)
    #        print('\n')
    #        for att in value:
    #            print(att)

    if(match):
        print('Face Matches!!')
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[12].id)
        engine.say("Face Regonised. Unlocking door.")
        engine.runAndWait()
        time.sleep(0.5)
        GPIO.output(relay, 0)
        sendLog("Face Matched")
        time.sleep(5)
        GPIO.output(relay, 1)

    else:
        print('Unmatched Faces')
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[12].id)
        engine.say("Face Not Recognized.")
        engine.runAndWait()
        time.sleep(0.5)
        SendMail(photo)
        GPIO.output(relay, 1)
        sendLog("Unknown Face Detected.")

