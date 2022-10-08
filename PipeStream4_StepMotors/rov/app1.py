from flask import Flask, render_template, Response, request, jsonify
from camera import Camera
import RPi.GPIO as GPIO # Import the GPIO Library
import time # Import the Time library
import serial
import pigpio

SERVO_V = 21
SERVO_H = 20
pi = pigpio.pi()

#ser = serial.Serial(
##               port='/dev/ttyS0',
#               baudrate = 9600,
#               parity=serial.PARITY_NONE,
 #              stopbits=serial.STOPBITS_ONE,
 #              bytesize=serial.EIGHTBITS,
 #              timeout=1
 #          )

GPIO.setmode(GPIO.BCM)
GPIO.cleanup()
pinMotorAForwards = 9
pinMotorABackwards = 10
pinMotorBForwards = 8
pinMotorBBackwards = 7
pinServoVert = 21
pinServoHor = 20

# How many times to turn the pin on and off each second
Frequency = 1000
# How long the pin says on each cycle, as a percent
Speed = 50
# Settng the duty cycle to 0 means the motors will not turn
Stop = 0

# Set the GPIO Pin mode to be Output
GPIO.setup(pinMotorAForwards, GPIO.OUT)
GPIO.setup(pinMotorABackwards, GPIO.OUT)
GPIO.setup(pinMotorBForwards, GPIO.OUT)
GPIO.setup(pinMotorBBackwards, GPIO.OUT)

# Set the GPIO to software PWM at 'Frequency' Hertz
pwmMotorAForwards = GPIO.PWM(pinMotorAForwards, Frequency)
pwmMotorABackwards = GPIO.PWM(pinMotorABackwards, Frequency)
pwmMotorBForwards = GPIO.PWM(pinMotorBForwards, Frequency)
pwmMotorBBackwards = GPIO.PWM(pinMotorBBackwards, Frequency)

# Start the software PWM with a duty cycle of 0 (i.e. not moving)
pwmMotorAForwards.start(Stop)
pwmMotorABackwards.start(Stop)
pwmMotorBForwards.start(Stop)
pwmMotorBBackwards.start(Stop)


def StopMotors():
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)

# Turn both motors forwards
def Forwards():
    pwmMotorAForwards.ChangeDutyCycle(Speed)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Speed)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)

# Turn both motors backwards
def Backwards():
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Speed)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Speed)

# Turn right
def Right():
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Speed)
    pwmMotorBForwards.ChangeDutyCycle(Speed)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)
    time.sleep(0.1)
    StopMotors()

# Turn left
def Left():
    pwmMotorAForwards.ChangeDutyCycle(Speed)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Speed)
    time.sleep(0.1)
    StopMotors()
    


app = Flask(__name__)

@app.route('/')
def execute():
    return render_template('index.html')



@app.route("/info", methods=['GET'])
def telemetry():
    return jsonify(voltage=3.43,
                   gyro_x=134.31,
                   gyro_y=256.66,
                   distance=123)
    

@app.route("/control", methods=['GET'])
def remoteControl():
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
        if (val > 100):
            Speed = 100
        elif (val < 0):
            Speed = 0
        else:
            Speed = val
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
