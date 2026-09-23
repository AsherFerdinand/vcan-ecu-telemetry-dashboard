# Virtual CAN Bus ECU Telemetry Simulator

An end-to-end automotive telemetry simulator built using Python and Linux **SocketCAN** (`vcan0`). 

This project emulates an Engine Control Unit (ECU) sending vehicle data over a CAN bus and a dashboard receiver that reads and decodes the messages in real time.

---

## 🚗 Architecture

* **`ecu_simulator.py`**: Sends engine data (RPM, Speed, Temperature) over `vcan0` at 100 Hz.
* **`dashboard_receiver.py`**: Listens to `vcan0`, parses raw hex payloads, and outputs formatted metrics.
* **Linux SocketCAN (`vcan0`)**: Virtual CAN interface handling frame transmission in the Linux kernel.

---

## 🛠️ Tech Stack

* **Language:** Python 3
* **Libraries:** `python-can`
* **OS / Framework:** Linux (WSL2 / Ubuntu), SocketCAN (`vcan`)
* **Protocol:** Controller Area Network (ISO 11898)

---

## 🚀 How to Run

### 1. Set Up Virtual CAN in Terminal
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

### 2. Install Dependencies
pip install python-can

### 3. Run the Simulation
Open two terminal tabs inside your can_project folder:

Tab 1 (Receiver):
python3 dashboard_receiver.py

Tab 2 (ECU Simulator):
python3 ecu_simulator.py

## 📌 Next Steps
[ ] Add a graphical user interface (GUI) dashboard using PyQt.

[ ] Implement .dbc file parsing using cantools.



