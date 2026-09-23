import time
import math
import can

def run_ecu():
    # Initialize CAN bus on vcan0 using SocketCAN
    try:
        bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
        print("ECU Simulator active on vcan0. Press Ctrl+C to stop.")
    except Exception as e:
        print(f"Error opening vcan0: {e}")
        return

    # Frame IDs (Standard 11-bit IDs)
    ENGINE_DATA_CAN_ID = 0x100  # Contains Speed & RPM
    BATTERY_DATA_CAN_ID = 0x200 # Contains Battery Temperature

    step = 0

    try:
        while True:
            # 1. Generate realistic dynamic data using sine functions
            rpm = int(1000 + 3000 * (0.5 + 0.5 * math.sin(step * 0.05)))  # 1000 to 4000 RPM
            speed = int(30 + 70 * (0.5 + 0.5 * math.sin(step * 0.02)))    # 30 to 100 km/h
            battery_temp = int(25 + 15 * (0.5 + 0.5 * math.sin(step * 0.01))) # 25°C to 40°C

            # 2. Pack Frame 0x100: Engine Data (8 bytes total)
            # Bytes 0-1: RPM (16-bit unsigned int, big-endian)
            # Byte 2: Speed (8-bit unsigned int)
            rpm_bytes = rpm.to_bytes(2, byteorder='big')
            speed_byte = speed.to_bytes(1, byteorder='big')
            
            # Combine payload with padding bytes up to 8 bytes DLC
            engine_payload = rpm_bytes + speed_byte + bytes([0x00] * 5)
            
            msg_engine = can.Message(
                arbitration_id=ENGINE_DATA_CAN_ID,
                data=engine_payload,
                is_extended_id=False
            )

            # 3. Pack Frame 0x200: Battery Data
            # Byte 0: Battery Temp (°C)
            battery_payload = bytes([battery_temp]) + bytes([0x00] * 7)
            
            msg_battery = can.Message(
                arbitration_id=BATTERY_DATA_CAN_ID,
                data=battery_payload,
                is_extended_id=False
            )

            # 4. Transmit on the bus
            bus.send(msg_engine)
            bus.send(msg_battery)

            step += 1
            time.sleep(0.01)  # 100 Hz broadcast rate

    except KeyboardInterrupt:
        print("\nStopping ECU Simulator.")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    run_ecu()
