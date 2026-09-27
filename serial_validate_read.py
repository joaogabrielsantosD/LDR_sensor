import serial
import time

# Connects to the opposite virtual end.
ser = serial.Serial('/tmp/ttyV1', 9600, timeout=1)
time.sleep(1)

# Simulates the main.c loop, incrementing `duty` from 0 to 255 in steps of 15.
duty = 0
while duty <= 255:
    for _ in range(100):  # SAMPLES = 100
        led_raw = 512
        ldr_raw = 400
        led_mv = (led_raw * 5000) >> 10
        ldr_mv = (ldr_raw * 5000) >> 10

        line = f"{duty},{led_raw},{led_mv},{ldr_raw},{ldr_mv},\r\n"
        ser.write(line.encode('utf-8'))
        time.sleep(0.001)

    duty += 15

print("Submission simulation completed.")