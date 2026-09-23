# Automotive Virtual CAN Bus ECU Simulator & Receiver

A lightweight, end-to-end automotive telemetry simulator built using Python and the Linux **SocketCAN** framework (`vcan0`). 

This project emulates an in-vehicle network where a simulated Engine Control Unit (ECU) publishes high-frequency sensor payloads (RPM, Vehicle Speed, Pack Temperature) over a virtual CAN bus, and a dashboard receiver node consumes, extracts, and decodes the signals in real time.

---

## 🚗 System Architecture

```text
[ ecu_simulator.py ] ---> ( CAN ID 0x100 / 0x200 ) ---> [ Linux vcan0 Kernel Socket ] ---> [ dashboard_receiver.py ]
ECU Simulator Node: Calculates dynamic vehicle telemetry and broadcasts 8-byte ISO 11898 CAN frames at 100 Hz.Linux SocketCAN (vcan0): Acts as the physical vehicle wiring harness, handling network arbitration and frame buffering at the kernel level.Dashboard Receiver Node: Intercepts CAN messages on vcan0, parses raw hex payloads using bit-shifting, and formats engine telemetry.🛠️ Tech Stack & Hardware/OS LayerOperating System: Linux (Ubuntu via WSL2 / Native Linux)Kernel Drivers: Linux SocketCAN (vcan kernel module)Language & Libraries: Python 3.10+, python-canProtocol: Controller Area Network (CAN Bus - ISO 11898)📊 Network Frame SpecificationsNodeCAN ID (Hex)Payload DLCTransmitted SignalsBroadcast RateEngine ECU0x1008 BytesRPM (Bytes 0-1), Speed km/h (Byte 3)100 HzBMS ECU0x2008 BytesTemperature °C (Byte 1)10 Hz🚀 Quick Start & Setup Guide1. Initialize Virtual CAN Interface (Linux Kernel)Bashsudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
2. Set Up Python EnvironmentBash# Clone the repository
git clone [https://github.com/AsherFerdinand/vcan-ecu-telemetry-dashboard.git](https://github.com/AsherFerdinand/vcan-ecu-telemetry-dashboard.git)
cd vcan-ecu-telemetry-dashboard

# Set up virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install python-can
3. Run the Network NodesOpen two separate terminal tabs:Terminal 1 (Start Dashboard Receiver):Bashpython3 dashboard_receiver.py
Terminal 2 (Start ECU Simulator):Bashpython3 ecu_simulator.py
💻 Inspecting Raw Bus TrafficTo monitor raw binary frames directly from the Linux SocketCAN kernel interface without Python decoding:Bashcandump vcan0
📌 Future Roadmap[ ] Implement .dbc (Database CAN) signal decoding using cantools.[ ] Add a visual desktop GUI cluster with live RPM and speed gauges.

