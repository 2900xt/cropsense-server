#!/usr/bin/env python3
"""
CropSense Sensor Simulator
Simulates sensor nodes sending data to the CropSense server API.
"""

import requests
import time
import random
import math
import argparse
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Baseline values for realistic simulation
BASELINES = {
    'temperature': 20.0,      # °C
    'humidity': 35.0,         # %
    'pressure': 101.0,        # kPa
    'gasResistance': 150.0,   # KOhm (healthy plant baseline)
    'mq2_r0': 320.0,          # Ohm
}

class SensorSimulator:
    def __init__(self, name, location, plant_id, disease_status='healthy'):
        self.name = name
        self.location = location
        self.plant_id = plant_id
        self.disease_status = disease_status
        self.time_offset = random.uniform(0, 2 * math.pi)
        self.registered = False

        # Diseased plants have lower gas resistance
        self.gas_resistance_base = 150.0 if disease_status == 'healthy' else 50.0

    def register(self):
        """Register the sensor with the server."""
        try:
            response = requests.post(f"{BASE_URL}/register", json={
                'name': self.name,
                'location': self.location
            })
            if response.status_code == 200:
                print(f"[{self.name}] Registered successfully")
                self.registered = True
            else:
                print(f"[{self.name}] Registration failed: {response.json()}")
        except requests.exceptions.ConnectionError:
            print(f"[{self.name}] Connection failed - is the server running?")

    def generate_reading(self):
        """Generate realistic sensor readings with natural variation."""
        t = time.time() + self.time_offset

        # Temperature varies slowly over time (simulating day/night cycle sped up)
        temp_variation = 2 * math.sin(t / 60) + random.gauss(0, 0.3)
        temperature = BASELINES['temperature'] + temp_variation

        # Humidity inversely related to temperature
        humidity_variation = -1.5 * math.sin(t / 60) + random.gauss(0, 0.5)
        humidity = BASELINES['humidity'] + humidity_variation

        # Pressure changes slowly
        pressure_variation = 0.5 * math.sin(t / 300) + random.gauss(0, 0.05)
        pressure = BASELINES['pressure'] + pressure_variation

        # Gas resistance - key indicator for plant health
        gas_variation = random.gauss(0, self.gas_resistance_base * 0.1)
        gas_resistance = self.gas_resistance_base + gas_variation

        # MQ2 sensor values
        mq2_r0 = BASELINES['mq2_r0'] + random.gauss(0, 5)
        mq2_rs = mq2_r0 * (3 + random.gauss(0, 0.2))
        mq2_ratio = mq2_rs / mq2_r0
        mq2_delta = random.gauss(0.15, 0.05)
        mq2_variance = random.gauss(3.0, 0.5)
        mq2_baseline = random.gauss(1.35, 0.1)

        return {
            'name': self.name,
            'plant_id': self.plant_id,
            'disease_status': self.disease_status,
            'timestamp': int(time.time() * 1000000),  # Microseconds
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'pressure': round(pressure, 3),
            'gasResistance': round(gas_resistance, 2),
            'mq2_rs': round(mq2_rs, 2),
            'mq2_ratio': round(mq2_ratio, 3),
            'mq2_r0': round(mq2_r0, 1),
            'mq2_delta': round(mq2_delta, 4),
            'mq2_variance': round(mq2_variance, 5),
            'mq2_baseline': round(mq2_baseline, 4)
        }

    def send_reading(self):
        """Send a reading to the server."""
        if not self.registered:
            self.register()

        reading = self.generate_reading()
        try:
            response = requests.post(f"{BASE_URL}/update", json=reading)
            if response.status_code == 200:
                print(f"[{self.name}] Sent: temp={reading['temperature']}°C, "
                      f"humidity={reading['humidity']}%, gas={reading['gasResistance']}kΩ")
            else:
                # Server may have restarted - try re-registering
                print(f"[{self.name}] Update failed, re-registering...")
                self.registered = False
                self.register()
                # Retry the update
                response = requests.post(f"{BASE_URL}/update", json=reading)
                if response.status_code == 200:
                    print(f"[{self.name}] Sent: temp={reading['temperature']}°C, "
                          f"humidity={reading['humidity']}%, gas={reading['gasResistance']}kΩ")
                else:
                    print(f"[{self.name}] Update still failed: {response.json()}")
        except requests.exceptions.ConnectionError:
            print(f"[{self.name}] Connection failed")


def main():
    parser = argparse.ArgumentParser(description='CropSense Sensor Simulator')
    parser.add_argument('--url', default='http://localhost:5000',
                        help='Server URL (default: http://localhost:5000)')
    parser.add_argument('--interval', type=float, default=2.0,
                        help='Update interval in seconds (default: 2.0)')
    parser.add_argument('--sensors', type=int, default=3,
                        help='Number of sensors to simulate (default: 3)')
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url

    # Create simulated sensors
    sensors = []
    for i in range(args.sensors):
        sensor_num = i + 1
        disease = 'healthy' if i % 3 != 2 else 'infected'  # Every 3rd sensor is infected
        sensor = SensorSimulator(
            name=f'sensor_{sensor_num:02d}',
            location=f'greenhouse_zone_{sensor_num}',
            plant_id=f'plant_{sensor_num:03d}',
            disease_status=disease
        )
        sensors.append(sensor)

    print(f"Starting simulation with {len(sensors)} sensors")
    print(f"Server: {BASE_URL}")
    print(f"Update interval: {args.interval}s")
    print("-" * 50)

    # Register all sensors
    for sensor in sensors:
        sensor.register()
        time.sleep(0.1)

    print("-" * 50)
    print("Sending readings... (Ctrl+C to stop)")
    print("-" * 50)

    # Main loop
    try:
        while True:
            for sensor in sensors:
                sensor.send_reading()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulation stopped")


if __name__ == '__main__':
    main()
