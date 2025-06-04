import RPi.GPIO as GPIO
import time
import datetime
import threading
import dht11

# GPIO Ayarları
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# === PIN TANIMLARI ===
TRIG = 23
ECHO = 24
BUZZER = 18
DHT_PIN = 4
SERVO_PIN = 25

# === GPIO Kurulumu ===
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(BUZZER, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# === DHT11 Başlatma ===
dht_instance = dht11.DHT11(pin=DHT_PIN)

# === Servo Motor PWM Başlatma ===
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
servo.start(0)

# === Global Değişkenler ===
sicaklik_degeri = 0.0
nem_degeri = 0.0
mesafe_degeri = 0.0
sicaklik_okumalari = []

# === Ortalama Hesabı ===
def ortalama(veriler, limit=5):
    if len(veriler) > limit:
        veriler.pop(0)
    return sum(veriler) / len(veriler)

# === Servo Açısını Ayarlama ===
def servo_goto(angle):
    duty = 2 + (angle / 18)
    GPIO.output(SERVO_PIN, True)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.4)
    GPIO.output(SERVO_PIN, False)
    time.sleep(0.1)

# === Sıcaklık & Nem Ölçümü ===
def sicaklik_nem_olc():
    global sicaklik_degeri, nem_degeri
    while True:
        try:
            result = dht_instance.read()
            if result.is_valid():
                sicaklik_okumalari.append(result.temperature)
                sicaklik_degeri = ortalama(sicaklik_okumalari)
                nem_degeri = result.humidity
        except:
            print("DHT11 hatası!")
        time.sleep(2)

# === Radar Tarama & Mesafe Ölçüm ===
def radar_tarama():
    global mesafe_degeri
    while True:
        for aci in range(0, 121, 30):  # 0-30-60-90-120 derece
            servo_goto(aci)
            try:
                GPIO.output(TRIG, True)
                time.sleep(0.00001)
                GPIO.output(TRIG, False)

                while GPIO.input(ECHO) == 0:
                    pulse_start = time.time()
                while GPIO.input(ECHO) == 1:
                    pulse_end = time.time()

                pulse_duration = pulse_end - pulse_start
                mesafe = pulse_duration * 17150
                mesafe = round(mesafe, 2)
                mesafe_degeri = mesafe

                now = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Açı: {aci}° | Mesafe: {mesafe:.2f} cm | Sıcaklık: {sicaklik_degeri:.1f}°C | Nem: {nem_degeri:.1f}%")

                # === Karar Mekanizması ===
                if mesafe < 10 and sicaklik_degeri > 30:
                    print("ALARM: Yüksek sıcaklık ve yakın nesne!")
                    GPIO.output(BUZZER, True)
                    time.sleep(0.3)
                    GPIO.output(BUZZER, False)
                elif mesafe < 10 or sicaklik_degeri > 30:
                    print("UYARI: Orta seviye tehlike.")
                    GPIO.output(BUZZER, True)
                    time.sleep(0.1)
                    GPIO.output(BUZZER, False)
                else:
                    GPIO.output(BUZZER, False)

                time.sleep(1)

            except:
                print("Radar ölçüm hatası!")
                GPIO.output(BUZZER, False)

# === ANA PROGRAM ===
try:
    print("Radar Sistemi Başlatılıyor...")

    # Thread'ler
    t1 = threading.Thread(target=sicaklik_nem_olc)
    t2 = threading.Thread(target=radar_tarama)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

except KeyboardInterrupt:
    print("Çıkış yapılıyor...")
finally:
    servo.stop()
    GPIO.cleanup()
