sudo apt update && sudo apt upgrade -y
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
ip link show vcan0
sudo apt update && sudo apt install python3-pip can-utils -y
pip install python-can cantools
sudo apt update
sudo apt install python3-venv python3-full -y
# 1. Create a project directory and enter it
mkdir ~/can_project
cd ~/can_project
# 2. Create the virtual environment (named 'venv')
python3 -m venv venv
# 3. Activate the environment
source venv/bin/activate
pip install python-can cantools
cd ~/can_project
source venv/bin/activate
python3 dashboard_receiver.py
code .
cd ~/can_project
source venv/bin/activate
python3 ecu_simulator.py
cd ~/can_project
source venv/bin/activate
python3 ecu_simulator.py
cd ~/can_project
source venv/bin/activate
python3 dashboard_receiver.py
cd ~/can_project
source venv/bin/activate
python3 dashboard_receiver.py
candump vcan0
candump vcan0
