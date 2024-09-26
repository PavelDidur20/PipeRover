from flask import Flask, render_template, Response, request, jsonify, send_file
import time
import serial
import pigpio
from threading import Thread, Event
import subprocess
import signal
import os
import os.path as path
import picamera
import datetime
import logging
from readline import ReadLine

# Определение пинов
SERVO_V = 21
SERVO_H = 20
MOT_FWD_A = 9
MOT_FWD_B = 10
MOT_BWD_A = 8
MOT_BWD_B = 7
LED = 4

# Настройки частоты и ШИМ
FRQ = 1000
DUTY = 64

# Путь к скрипту камеры
CAMSTREAM_SCRIPT = '/home/pi/rov/script.sh'

# Инициализация pigpio
pi = pigpio.pi()

# Настройка PWM для двигателей и светодиодов
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

# Настройка последовательного порта
try:
    ser = serial.Serial(
        port='/dev/ttyS0',
        baudrate=9600
    )
except serial.SerialException as e:
    logging.error(f"Ошибка при инициализации последовательного порта: {e}")
    ser = None

# Глобальные переменные для хранения предыдущих данных
prev_gyro = "0.0"
prev_metres = "0.0"
prev_batt = "0.0"

# Вспомогательные функции
def kill_proc(proc_name):
    """Остановка процесса по имени."""
    try:
        p = subprocess.Popen(['ps', '-ax'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            if proc_name in str(line, encoding='utf-8'):
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)
    except Exception as e:
        logging.error(f"Ошибка при остановке процесса {proc_name}: {e}")

def set_servo_position(servo_pin, new_position):
    """Установка позиции сервопривода."""
    pi.set_servo_pulsewidth(servo_pin, new_position)
    logging.info(f"Сервопривод {servo_pin} установлен в позицию {new_position}")

def stop_motors():
    """Остановка всех моторов."""
    pi.set_PWM_dutycycle(MOT_FWD_A, 0)
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0)

def forwards():
    """Движение вперед."""
    pi.set_PWM_dutycycle(MOT_FWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_FWD_B, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0)

def backwards():
    """Движение назад."""
    pi.set_PWM_dutycycle(MOT_FWD_A, 0)
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_B, DUTY)

def right():
    """Поворот направо."""
    pi.set_PWM_dutycycle(MOT_FWD_A, 0)
    pi.set_PWM_dutycycle(MOT_FWD_B, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_BWD_B, 0)
    time.sleep(0.1)
    stop_motors()

def left():
    """Поворот налево."""
    pi.set_PWM_dutycycle(MOT_FWD_A, DUTY)
    pi.set_PWM_dutycycle(MOT_FWD_B, 0)
    pi.set_PWM_dutycycle(MOT_BWD_A, 0)
    pi.set_PWM_dutycycle(MOT_BWD_B, DUTY)
    time.sleep(0.1)
    stop_motors()

# Flask сервер
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/info", methods=['GET'])
def telemetry():
    """Получение данных телеметрии от Arduino."""
    global prev_batt, prev_gyro, prev_metres

    if ser is None:
        return jsonify(voltage=prev_batt, gyro_x=prev_gyro, distance=prev_metres)

    try:
        rl = ReadLine(ser)
        data1 = rl.readline()
        data2 = rl.readline()
        data3 = rl.readline()
        serial_data = data1 + data2 + data3
        data_str = str(serial_data, 'utf-8')
    except Exception as e:
        logging.error(f"Ошибка при чтении данных с последовательного порта: {e}")
        return jsonify(voltage=prev_batt, gyro_x=prev_gyro, distance=prev_metres)

    battery = extract_value(data_str, 'Bat', prev_batt)
    gyro = extract_value(data_str, 'gyro', prev_gyro)
    metres = extract_value(data_str, 'Distance', prev_metres)

    prev_batt = battery
    prev_gyro = gyro
    prev_metres = metres

    return jsonify(voltage=battery, gyro_x=gyro, distance=metres)

def extract_value(data_str, keyword, prev_value):
    """Извлечение значения из строки данных."""
    index = data_str.find(keyword)
    if index != -1:
        return data_str[index+len(keyword)+1:index+len(keyword)+6]
    return prev_value

@app.route("/control", methods=['GET'])
def remote_control():
    """Обработка управляющих команд для робота."""
    global DUTY
    var = request.args.get('var')
    val = int(request.args.get('val'))

    if var == "car":
        car_control(val)
    elif var == "servo":
        set_servo_position(SERVO_V, val)
    elif var == "servo1":
        set_servo_position(SERVO_H, val)
    elif var == "speed":
        DUTY = max(0, min(val, 240))
    elif var == "led":
        pi.set_PWM_dutycycle(LED, max(0, min(val, 255)))

    return '', 204

def car_control(val):
    """Обработка движения машины."""
    if val == 1:
        forwards()
    elif val == 2:
        left()
    elif val == 3:
        stop_motors()
    elif val == 4:
        right()
    elif val == 5:
        backwards()

@app.route("/snapshot", methods=['GET'])
def snapshot():
    """Сделать снимок с камеры."""
    filename = f'{cwd}/{datetime.datetime.now()}.jpg'

    try:
        subprocess.run([CAMSTREAM_SCRIPT, 'stop'])
        time.sleep(0.5)

        with picamera.PiCamera() as camera:
            camera.resolution = (1920, 1080)
            camera.rotation = 90
            camera.start_preview()
            camera.capture(filename)
            camera.stop_preview()

    except picamera.exc.PiCameraMMALError as e:
        logging.error(f"Ошибка камеры: {e}")
        return jsonify({"error": "Ошибка камеры"})

    finally:
        subprocess.run([CAMSTREAM_SCRIPT, 'start'])

    if not path.exists(filename):
        logging.error("Файл не найден")
        return jsonify({"error": "Снимок не сделан"})

    return send_file(filename)

def client_monitor():
    """Мониторинг подключения клиента и остановка моторов, если клиент отключен."""
    while True:
        try:
            cmd_out = subprocess.run(['hostapd_cli', 'all_sta'], stdout=subprocess.PIPE).stdout.decode('utf-8')
            if len(cmd_out) <= 27:
                stop_motors()
        except Exception as e:
            logging.error(f"Ошибка мониторинга клиента: {e}")
        time.sleep(0.5)

if __name__ == '__main__':
    client_thread = Thread(target=client_monitor)
    client_thread.start()
    subprocess.run([CAMSTREAM_SCRIPT, 'start'])
    app.run(debug=False, host='0.0.0.0', threaded=True)

    
