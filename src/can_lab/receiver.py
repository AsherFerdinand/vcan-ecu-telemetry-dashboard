"""Decode bus observations without aggregating or inventing missing signals."""
from .codec import SyntheticCodec


def receive(bus, *, count=None, timeout_s=5):
    if count is not None and count < 1:
        raise ValueError('count must be positive')
    codec = SyntheticCodec()
    received = 0
    while count is None or received < count:
        message = bus.recv(timeout=timeout_s)
        if message is None:
            raise TimeoutError('no CAN frame received within timeout')
        yield codec.decode(message)
        received += 1
