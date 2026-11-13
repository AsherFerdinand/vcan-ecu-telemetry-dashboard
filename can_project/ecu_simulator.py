"""Compatibility entry point for the original SocketCAN ECU simulator."""
from can_lab.cli import main


def run_ecu():
    return main(['simulate'])


if __name__ == '__main__':
    raise SystemExit(run_ecu())
