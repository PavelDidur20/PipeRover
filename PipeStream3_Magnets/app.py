from flask import Flask, render_template, Response, request, jsonify, send_file
import time # Import the Time library
import serial
import pigpio
from threading import Thread, Event
import subprocess, signal
import RPi.GPIO as GPIO

from readline import ReadLine
import picamera
import datetime
import logging
import os.path as path

SERVO_V = 21
SERVO_H = 20
MAGNET_UP = 5
MAGNET_DOWN = 6

subprocess.run(['pigpiod', '-s', '10'])
pi = pigpio.pi()


MOT_FWD_A = 9
MOT_FWD_B = 10
MOT_BWD_A = 8
MOT_BWD_B = 7

SERVO_V = 21
SERVO_H = 20
LED = 4


CAMSTREAM_SCRIPT = '/home/pi/Desktop/UCTRONICS_Smart_Robot_Car_RaspberryPi-master/mjpg-streamer.sh'

serial_data = ""
EMPTY_DATA = "0.0"


prevGyroX = EMPTY_DATA
prevGyroY = EMPTY_DATA
prevMetres = EMPTY_DATA
prevBatt = EMPTY_DATA




ser = serial.Serial(
               port='/dev/ttyS0',
               baudrate = 9600
           )
           
#logging.basicConfig(filename="app.txt", filemode='a', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)


pi.set_mode(MAGNET_UP, pigpio.OUTPUT)
pi.set_mode(MAGNET_DOWN, pigpio.OUTPUT)
pi.write(MAGNET_UP, 1)
pi.write(MAGNET_DOWN, 1)


FRQ = 1000
DUTY = 64

pi.set_PWM_dutycycle(MOT_FWD_A, 0)
pi.set_PWM_dutycycle(MOT_FWD_B, 0)
pi.set_PWM_dutycycle(MOT_BWD_A, 0)
pi.set_PWM_dutycycle(MOT_BWD_B, 0)

pi.set_PWM_frequency(MOT_FWD_A, FRQ)
pi.set_PWM_frequency(MOT_FWD_B, FRQ)
pi.set_PWM_frequency(MOT_BWD_A, FRQ)
pi.set_PWM_frequency(MOT_BWD_B, FRQ)



def kill_proc(proc):
        p = subprocess.Popen(['ps', '-A'],  stdout=subprocess.PIPE)
        out,err = p.communicate()
        for line in out.splitlines():
            if (proc in str(line, encoding='utf-8')):
                pid = int(line.split(None,1)[0])
                os.kill(pid, signal.SIGKILL)
                
        
def setServoPosition(servoPin, newPosition):
        pi.set_servo_pulsewidth(servoPin, newPosition)
        print(newPosition)
    

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



    
 
serialEvent = Event()


@app.route("/info", methods=['GET'])
def telemetry():

    global prevBatt
    global prevGyro
    global prevMetres
    
    gx = None
    gy = None
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
    
    
    index_g = data_str.find('gyroX')
    if (index_g is not -1):
        gx = data_str[index_g+6:index_g+11]
    else:
        gy_ = EMPTY_DATA
    
    index_g1 = data_str.find('gyroY')
    if (index_g1 is not -1):
        gy = data_str[index_g1+6:index_g1+11]
    else:
        gy = EMPTY_DATA
        
    
    index_d = data_str.find('Distance')
    if (index_d is not -1):
        metres = data_str[index_d+9:index_d+15]
    else:
        metres = EMPTY_DATA
    

 
    if (index_g is not -1):
        prevGyroX = gx
    else:
        gx = prevGyroX
        
    if (index_g1 is not -1):
        prevGyroY = gy
    else:
        gy = prevGyroY
        
    if (index_b is not -1):
        prevBatt = battery
    else:
        battery = prevBatt
        
    if (index_d is not -1):
        prevMetres = metres
    else:
        metres = prevMetres
   
   
    return jsonify(voltage=battery,
                   gyro_x=gy,
                   gyro_y=0,
                   gyro_z=gx,
                   distance=metres)
    

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
        if (val > 240):
            DUTY = 240
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
             
    elif (var == "magnet_up"):
        if (val == 1):
            print("MAGNET UP = 0")
            pi.write(MAGNET_UP, 0)
            
        if (val == 0):
            print("MAGNET UP = 1")
            pi.write(MAGNET_UP, 1)
    
    elif (var == "magnet_down"):
        if (val == 1):
            print("MAGNET DOWN = 0")
            pi.write(MAGNET_DOWN, 0)
            
        if (val == 0):
            print("MAGNET DOWN = 1")
            pi.write(MAGNET_DOWN, 1)
          
            
            
        

    return('', 204)


    
def clientIsHere():
    while(1):
        cmd_out = subprocess.run(['hostapd_cli', 'all_sta'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        if (not len(cmd_out) > 27):
            StopMotors()
        time.sleep(0.5)

        
@app.route("/snapshot", methods=['GET'])
def snapshot():

    filename = "/home/pi/rov" + str(datetime.datetime.now()) + ".jpg"
    subprocess.run([CAMSTREAM_SCRIPT, 'stop'])
    kill_proc(CAMSTREAM_SCRIPT)
    kill_proc('mjpg-streamer')
    
    with picamera.PiCamera() as camera:
        try:
            camera.resolution = (3280,2464)
            camera.rotation = 270
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
    

        
    
