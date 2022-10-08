from flask import Flask, render_template, Response, request, jsonify
from camera import Camera
import RPi.GPIO as GPIO # Import the GPIO Library
import time # Import the Time library
import serial
import pigpio

SERVO_V = 21
SERVO_H = 20
pi = pigpio.pi()

ser = serial.Serial(
               port='/dev/ttyS0',
               baudrate = 9600,
               parity=serial.PARITY_NONE,
               stopbits=serial.STOPBITS_ONE,
               bytesize=serial.EIGHTBITS,
               timeout=1
           )
MOT_FWD_A = 9
MOT_FWD_B = 10
MOT_BWD_A = 8
MOT_BWD_B = 7
SERVO_V = 21
SERVO_H = 20
LED = 4

FRQ = 1000
DUTY = 64


gyroX = None
gyroY = None
battery = None
mileage = None

pi.set_PWM_dutycycle(MOT_FWD_A, 0)
pi.set_PWM_dutycycle(MOT_FWD_B, 0)
pi.set_PWM_dutycycle(MOT_BWD_A, 0)
pi.set_PWM_dutycycle(MOT_BWD_B, 0)

pi.set_PWM_frequency(MOT_FWD_A, FRQ)
pi.set_PWM_frequency(MOT_FWD_B, FRQ)
pi.set_PWM_frequency(MOT_BWD_A, FRQ)
pi.set_PWM_frequency(MOT_BWD_B, FRQ)

pi.set_PWM_dutycycle(LED, 0)
pi.set_PWM_frequency(LED, 50)

def StopMotors():
    pi.set_PWM_dutycycle(MOT_FWD_A, 0)
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0)


# Turn both motors forwards AF = 1 AB = 0 BF = 1 BB = 0
def Forwards(): 
    print(DUTY)
    pi.set_PWM_dutycycle(MOT_FWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_FWD_B, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0)

def Backwards():
    pi.set_PWM_dutycycle(MOT_FWD_A, 0)
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_B, DUTY)

# Turn right
def Right():
    pi.set_PWM_dutycycle(MOT_FWD_A, 0) 
    pi.set_PWM_dutycycle(MOT_FWD_B, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0) 
    time.sleep(0.1)
    StopMotors()

# Turn left
def Left():
    pi.set_PWM_dutycycle(MOT_FWD_A, DUTY) 
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, DUTY)     
    time.sleep(0.1)
    StopMotors()
    


app = Flask(__name__)

@app.route('/')
def execute():
    return render_template('index.html')



@app.route("/info", methods=['GET'])
def telemetry():
    
    global battery
    global gyroX
    global gyroY
    global mileage
    return jsonify(voltage=battery,
                   gyro_x=gyroX,
                   gyro_y=gyroY,
                   distance=mileage)
    

@app.route("/control", methods=['GET'])
def remoteControl():
    global DUTY
    var =request.args.get('var')
    val = int(request.args.get('val'))
    print("var = %s \n val = %d" % (var, val)) 
    if (var == "car"):
        if (val == 1):
            Forwards()
        elif (val == 2):
            Left()
        elif  (val == 3):
            StopMotors()
        elif (val == 4):
            Right()
        elif (val == 5):
            Backwards()

    elif (var == "servo"):
        if (val < 500):
            pi.set_servo_pulsewidth(SERVO_V, 500)
        elif (val > 2500):
            pi.set_servo_pulsewidth(SERVO_V, 2500)
        else:
            pi.set_servo_pulsewidth(SERVO_V, val)
            
    elif (var == "servo1"):
        if (val < 500):
            pi.set_servo_pulsewidth(SERVO_H, 500)
        elif (val > 2500):
            pi.set_servo_pulsewidth(SERVO_H, 2500)
        else:
            pi.set_servo_pulsewidth(SERVO_H, val)
        
    elif (var == "speed"):
        if (val > 255):
            DUTY = 255
        elif (val < 0):
            DUTY = 0
        else:
            DUTY = val
    elif (var == "led"):
         if (val > 255):
             pi.set_PWM_dutycycle(LED,255)
         elif (val < 0):
             pi.set_PWM_dutycycle(LED, 0)
         else:
             pi.set_PWM_dutycycle(LED, val)

    return('', 204)


def gen(camera):
	while True:
		frame = camera.get_frame()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
	return Response(gen(Camera()),
		mimetype='multipart/x-mixed-replace; boundary=frame')



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True)
