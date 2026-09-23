import can

def run_dashboard():
    # Connect to the virtual bus
    try:
        bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
        print("Dashboard Receiver listening on vcan0...\n")
    except Exception as e:
        print(f"Error opening vcan0: {e}")
        return

    ENGINE_DATA_CAN_ID = 0x100
    BATTERY_DATA_CAN_ID = 0x200

    try:
        while True:
            # Block until a frame is received on the bus
            msg = bus.recv()

            if msg is None:
                continue

            # Process Engine Data Frame
            if msg.arbitration_id == ENGINE_DATA_CAN_ID:
                data = msg.data
                # Unpack Bytes 0-1 for RPM (Big-Endian)
                rpm = int.from_bytes(data[0:2], byteorder='big')
                # Unpack Byte 2 for Speed
                speed = data[2]
                
                print(f"[0x100 ENGINE]  | RPM: {rpm:4d} rpm  | Speed: {speed:3d} km/h")

            # Process Battery Data Frame
            elif msg.arbitration_id == BATTERY_DATA_CAN_ID:
                battery_temp = msg.data[0]
                
                print(f"[0x200 BATTERY] | Temp: {battery_temp:2d} °C")

    except KeyboardInterrupt:
        print("\nStopping Dashboard Receiver.")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    run_dashboard()
