"""Compatibility entry point for the original SocketCAN dashboard receiver."""
from can_lab.cli import main


def run_dashboard():
    return main(['receive'])


if __name__ == '__main__':
    raise SystemExit(run_dashboard())
