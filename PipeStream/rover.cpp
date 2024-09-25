#include <Wire.h>
#include "Kalman.h"


Kalman kalmanX;
Kalman kalmanY;

const uint8_t IMUAddress = 0x68;


int16_t accX, accY, accZ;
int16_t tempRaw;
int16_t gyroX, gyroY, gyroZ;

float accXangle;   // Угол, вычисленный по акселерометру
float accYangle;
float temp;        
float gyroXangle = 180; 
float gyroYangle = 180;
float compAngleX = 180; 
float compAngleY = 180;
float kalAngleX;   
float kalAngleY;

uint32_t timer;

int ch1, ch2, ch3, ch4;

// Массивы для времени обнаружения фронтов и длины импульсов
volatile int rxPrev[4] = {0, 0, 0, 0};
volatile int rxVal[4] = {0, 0, 0, 0};


boolean inclineStateLeft = false;
boolean inclineStateRight = false;


unsigned long time;
unsigned long prevTime;

const unsigned long REFRESH_INTERVAL = 1000; // Интервал обновления, мс
const int numReadings = 30;   // Количество чтений для расчета среднего
const float voltageMultiplier = 0.0122; // Коэффициент для расчета напряжения


int readings[numReadings] = {0}; // Массив для хранения чтений
int readIndex = 0;               // Индекс текущего чтения
int total = 0;                   // Сумма всех значений
float averageBat = 0.0;          // Среднее напряжение


void gohome();
void getGyro();
bool isForward();
bool isBackward();


void setup() {
    Wire.begin();
    Serial.begin(9600);
    Serial.setTimeout(1);

    // Инициализация IMU
    Wire.beginTransmission(IMUAddress);
    Wire.write(0x6B); // PWR_MGMT_1
    Wire.write(0);    // Включение MPU-6050
    Wire.endTransmission(true);

    kalmanX.setAngle(180); 
    kalmanY.setAngle(180);
    timer = micros();      

   
    pinMode(2, INPUT);  // PCINT18/INT0
    pinMode(3, INPUT);  // PCINT19/INT1
    pinMode(4, INPUT);  // PCINT20
    pinMode(8, INPUT);  // PCINT0
    pinMode(14, INPUT); // Уровень напряжения
    pinMode(17, INPUT); // Датчик импульсов
    pinMode(5, OUTPUT); // ШИМ выходы
    pinMode(6, OUTPUT);
    pinMode(9, OUTPUT);
    pinMode(10, OUTPUT);
    pinMode(11, OUTPUT); // Свет

    // Настройка ШИМ частот
    TCCR2B = 0b00000010;  // 4 кГц на пинах D3 и D11
    TCCR2A = 0b00000001;  // phase correct
    TCCR1A = 0b00000001;  // 8bit ШИМ на пинах D5 и D6 (976 Гц)
    TCCR1B = 0b00001011;  // x64 fast pwm

    // Настройка прерываний
    EICRA |= (1 << ISC10) | (1 << ISC00);   // INT1 и INT0 на изменение фронта
    EIMSK |= (1 << INT1) | (1 << INT0);     // Включаем прерывания

    // Включаем маски прерываний для PCINT
    PCICR |= (1 << PCIE2) | (1 << PCIE1) | (1 << PCIE0);
    PCMSK0 |= 1 << PCINT0;
    PCMSK1 |= 1 << PCINT11;
    PCMSK2 |= 1 << PCINT20;

    // Инициализируем массив чтений для расчета среднего
    for (int i = 0; i < numReadings; i++) {
        readings[i] = 0;
    }
}

// Получение данных с гироскопа
void getGyro() {
    Wire.beginTransmission(IMUAddress);
    Wire.write(0x3B); // Начало с регистра ACCEL_XOUT_H
    Wire.endTransmission(false);
    Wire.requestFrom(IMUAddress, 14, true);

    accX = Wire.read() << 8 | Wire.read();
    accY = Wire.read() << 8 | Wire.read();
    accZ = Wire.read() << 8 | Wire.read();
    tempRaw = Wire.read() << 8 | Wire.read();
    gyroX = Wire.read() << 8 | Wire.read();
    gyroY = Wire.read() << 8 | Wire.read();
    gyroZ = Wire.read() << 8 | Wire.read();

    accYangle = (atan2(accX, accZ) + PI) * RAD_TO_DEG;
    accXangle = (atan2(accY, accZ) + PI) * RAD_TO_DEG;

    float gyroXrate = (float)gyroX / 131.0;
    float gyroYrate = -((float)gyroY / 131.0);

    // Обновляем углы по гироскопу
    gyroXangle += gyroXrate * ((float)(micros() - timer) / 1000000);
    gyroYangle += gyroYrate * ((float)(micros() - timer) / 1000000);

    // Рассчитываем углы с фильтром Калмана
    kalAngleX = kalmanX.getAngle(accXangle, gyroXrate, (float)(micros() - timer) / 1000000);
    kalAngleY = kalmanY.getAngle(accYangle, gyroYrate, (float)(micros() - timer) / 1000000);

    timer = micros(); // Обновляем время
}

// Главный цикл программы
void loop() {
    getGyro(); // Получаем данные гироскопа

    // Чтение напряжения
    total -= readings[readIndex];
    readings[readIndex] = analogRead(A0); // Чтение сенсора
    total += readings[readIndex];
    readIndex = (readIndex + 1) % numReadings; // Циклический индекс

    averageBat = (total / numReadings) * voltageMultiplier; // Рассчитываем среднее напряжение

    if (millis() - lastRefreshTime >= REFRESH_INTERVAL) {
        lastRefreshTime += REFRESH_INTERVAL;

        // Вывод данных
        Serial.println("gyroX:" + String(kalAngleX));
        Serial.println("gyroY:" + String(kalAngleY));
        Serial.println("Distance:" + String((double)count / 1340));
        Serial.println("Bat:" + String(averageBat));
    }

    if (averageBat < 10) {
        gohome(); // Возвращаемся домой при низком уровне заряда
    }

    analogWrite(11, 100); // Включаем свет

    // Обновляем значения каналов с учетом пределов
    ch1 = constrain(int(0.51 * rxVal[0]), 0, 255);
    ch2 = constrain(int(0.51 * rxVal[1]), 0, 255);
    ch3 = constrain(int(0.51 * rxVal[2]), 0, 255);
    ch4 = constrain(int(0.51 * rxVal[3]), 0, 255);

    // Логика движения
    if (isForward() || isBackward()) {
        time = 0;
        prevTime = millis();
    } else {
        time = millis() - prevTime;
    }

    if (time > 300000) {
        gohome();
    }

    // Управление двигателями на основе углов
    if ((kalAngleX > 185) && isForward()) 
	{
        inclineStateLeft = true;
        analogWrite(10, ch4 - ch4 / 3); // Торможение левых двигателей
    }
    if ((int)kalAngleX == 180 && inclineStateLeft)
	
	{
        analogWrite(6, 0);
        analogWrite(10, 100);
        analogWrite(5, 100);
        delay(200);
        inclineStateLeft = false;
    }

    // Торможение правых двигателей при наклоне вправо
    if ((kalAngleX < 175) && isForward()) 
	{
      inclineStateRight = true; analogWrite(5, ch4 - ch4 / 3); 
	} 
	if ((int)kalAngleX == 180 && inclineStateRight) { analogWrite(6, 0); analogWrite(10, 100); analogWrite(5, 100); delay(200); inclineStateRight = false; } }


void gohome ()
{
  while ((digitalRead(2) == LOW && digitalRead(4) == LOW) && ((int)(count) > 0))
  {
    Serial.println("Distance:" + String((double)count/1340));
    getGyro();
    analogWrite(11, 0); // тушим свет, экономия батарейки
    analogWrite(5, ch1=150);
    analogWrite(6, 0);
    analogWrite(9, ch3=150);
    analogWrite(10, 0);
	
    if (kalAngleX > 185)                    // едем задом и наклон вправо
    {
      inclineStateleft = true;
      analogWrite(5, 150);               //подрабатываем правыми двигателями
    }
	
    if ((kalAngleX == 180) && (inclineStateleft))     //поворот влево для выравнивания
    {
      analogWrite(5, 0);
      analogWrite(6, 100);
      delay(200);
      inclineStateleft = false;
    }

    if (kalAngleX < 175)                    // едем задом и наклон влево
    {
      inclineStateright = true;
      analogWrite(9, 150);                  //подрабатываем левыми двигателями
    }
    if ((kalAngleX == 180) && (inclineStateright))     //поворот вправо для выравнивания
    {
      analogWrite(9, 0);
      analogWrite(10, 100);
      delay(200);
      inclineStateright = false;
    }
  }
}

 bool isForward() { return kalAngleX > 180 && kalAngleX < 185; }

 bool isBackward() { return kalAngleX < 180 && kalAngleX > 175; }