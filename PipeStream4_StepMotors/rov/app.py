from flask import Flask, render_template, Response, request, jsonify, send_file
import time # Import the Time library
import serial
import pigpio
from threading import Thread, Event
import subprocess, signal

from readline import ReadLine
import picamera
import datetime
import logging
import os.path as path
import os

SERVO_V = 21
SERVO_H = 20


pi = pigpio.pi()

cwd = os.getcwd()

CAMSTREAM_SCRIPT =   '/home/pi/rov/script.sh'



ser = serial.Serial(
               port='/dev/ttyS0',
               baudrate = 9600
           )

    

serial_data = ""
EMPTY_DATA = "0.0"


prevGyro = EMPTY_DATA
prevMetres = EMPTY_DATA
prevBatt = EMPTY_DATA




STEP_A = 9
STEP_B = 8
DIR_A = 10
DIR_B = 7
SERVO_V = 21
SERVO_H = 20
LED = 4

FRQ =  200  # Change only Freq for steper motors
DUTY = 64




pi.set_mode(DIR_A, pigpio.OUTPUT)
pi.set_mode(DIR_B, pigpio.OUTPUT)

pi.set_PWM_dutycycle(LED, 0)
pi.set_PWM_frequency(LED, 50)



    
def kill_proc(proc):
        p = subprocess.Popen(['ps', '-ax'],  stdout=subprocess.PIPE)
        out,err = p.communicate()
        for line in out.splitlines():
            if (proc in str(line, encoding='utf-8')):
                pid = int(line.split(None,1)[0])
                os.kill(pid, signal.SIGKILL)
                
        
def setServoPosition(servoPin, newPosition):
        pi.set_servo_pulsewidth(servoPin, newPosition)
        print(newPosition)
    

def StopMotors():
    pi.set_PWM_frequency(STEP_A, 0)
    pi.set_PWM_frequency(STEP_B, 0)
    pi.write(STEP_A,0)
    pi.write(STEP_B,0)

def Forwards():
    pi.set_PWM_dutycycle(STEP_A, DUTY)
    pi.set_PWM_dutycycle(STEP_B, DUTY)

    pi.set_PWM_frequency(STEP_A, FRQ)
    pi.set_PWM_frequency(STEP_B, FRQ)
    pi.write(DIR_A, 1)
    pi.write(DIR_B, 0)
    

def Backwards():
    pi.set_PWM_dutycycle(STEP_A, DUTY)
    pi.set_PWM_dutycycle(STEP_B, DUTY)
    
    pi.set_PWM_frequency(STEP_A, FRQ)
    pi.set_PWM_frequency(STEP_B, FRQ)
    pi.write(DIR_A, 0)
    pi.write(DIR_B, 1)



def Right():
    pi.set_PWM_dutycycle(STEP_A, DUTY)
    pi.set_PWM_dutycycle(STEP_B, DUTY)  
    
    pi.set_PWM_frequency(STEP_A, FRQ)
    pi.set_PWM_frequency(STEP_B, FRQ)
    pi.write(DIR_A, 0)
    pi.write(DIR_B, 0)
    time.sleep(0.1)
    StopMotors()


def Left():
    pi.set_PWM_dutycycle(STEP_A, DUTY)
    pi.set_PWM_dutycycle(STEP_B, DUTY)
    
    pi.set_PWM_frequency(STEP_A, FRQ)
    pi.set_PWM_frequency(STEP_B, FRQ)
    pi.write(DIR_A, 1)
    pi.write(DIR_B, 1) 
    time.sleep(0.1)
    StopMotors()
    


app = Flask(__name__)

@app.route('/')
def execute():
    return render_template('index.html')



    
 
serialEvent = Event()


@app.route("/info", methods=['GET'])
def telemetry():

    global prevBatt
    global prevGyro
    global prevMetres
    
    gyro = None
    battery = None
    metres = None
    global serial_data
   
    
    rl = ReadLine(ser)
    data1 = rl.readline()
    data2 = rl.readline()
    data3 = rl.readline()
    
    serial_data =  data1+data2+data3
    #print(serial_data)
    
    data_str = str(serial_data, 'utf-8')
    
    index_b = data_str.find('Bat')
    if (index_b is not -1):
        battery = data_str[index_b+4:index_b+9]
    else:
        battery = EMPTY_DATA
    
    
    index_g = data_str.find('gyro')
    if (index_g is not -1):
        gyro = data_str[index_g+5:index_g+11]
    else:
        gyro = EMPTY_DATA
        
    
    index_d = data_str.find('Distance')
    if (index_d is not -1):
        metres = data_str[index_d+9:index_d+15]
    else:
        metres = EMPTY_DATA
    

 
    if (index_g is not -1):
        prevGyro = gyro
    else:
        gyro = prevGyro
        
    if (index_b is not -1):
        prevBatt = battery
    else:
        battery = prevBatt
        
    if (index_d is not -1):
        prevMetres = metres
    else:
        metres = prevMetres
   
   
    return jsonify(voltage=battery,
                   gyro_x=gyro,
                   distance=metres)
    

@app.route("/control", methods=['GET'])
def remoteControl():
    global FRQ
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
        if (val < 1100):
            setServoPosition(SERVO_V, 1100)
        elif (val > 2400):
            setServoPosition(SERVO_V, 2400)
        else:
            setServoPosition(SERVO_V, val)
            
    elif (var == "servo1"):
        if (val < 500):
            setServoPosition(SERVO_H, 500)
        elif (val > 2300):
            setServoPosition(SERVO_H, 2300)
        else:
            setServoPosition(SERVO_H, val)
        
    elif (var == "speed"):
        if (val > 1000):
            FRQ = 1000
        elif (val < 200):
            FRQ = 200
        else:
            FRQ = val
    elif (var == "led"):
         if (val > 255):
             pi.set_PWM_dutycycle(LED,255)
         elif (val < 0):
             pi.set_PWM_dutycycle(LED, 0)
         else:
             pi.set_PWM_dutycycle(LED, val)

    return('', 204)


    
def clientIsHere():
    while(1):
        cmd_out = subprocess.run(['hostapd_cli', 'all_sta'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        if (not len(cmd_out) > 27):
            StopMotors()
        time.sleep(0.5)


        
@app.route("/snapshot", methods=['GET'])
def snapshot():
    filename =  cwd + str(datetime.datetime.now()) + '.jpg'
    subprocess.run([CAMSTREAM_SCRIPT, 'stop'])
    time.sleep(0.5)
    
    with picamera.PiCamera() as camera:
        try:
            camera.resolution = (1920,1080)
            camera.rotation = 90
            camera.start_preview()
            camera.capture(filename)
            camera.stop_preview()
        except picamera.exc.PiCameraMMALError as e:
            print(e)
        
    if path.exists(filename) == False:
        print("FILE NOT FOUND")
            

    subprocess.run([CAMSTREAM_SCRIPT, 'start'])
    return send_file(filename)
    


if __name__ == '__main__':
    motorsThread = Thread(target=clientIsHere)
    motorsThread.start()
    subprocess.run([CAMSTREAM_SCRIPT, 'start'])
    app.run(debug=False, host='0.0.0.0', threaded=True)
    

        
    
