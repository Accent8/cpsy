from gpiozero import MCP3008

sensor = MCP3008(channel=0)

def voltage(sensor):
    return sensor.value * 3.3

def distance_cm(v):
    if v <= 0:
        return float('inf')
    return 60.5 * v ** -1.1

print("Press Enter to take a reading (Ctrl+C to quit).")
while True:
    line = input()
    if line.strip().lower() == 'q':
        break
    v = voltage(sensor)
    print(f"{v:.2f} V  ->  {distance_cm(v):.1f} cm")