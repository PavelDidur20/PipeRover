import picamera
import datetime
import time
import subprocess

#filename =  "/home/pi/rov" + str(datetime.datetime.now()) + ".jpg"
filename = "/home/pi/rov/MYIMG.JPG"
subprocess.run(['raspistill', '-rot', '90', '-o', filename ])

#with picamera.PiCamera() as camera:
#   try:
#        camera.resolution = (2592,1944)
#        camera.rotation = 90
#        camera.start_preview()
#        time.sleep(3)
#        camera.capture(filename)
#        camera.stop_preview()
#    except picamera.PiCameraError as e:
 #       print(e)
            

