"""DBC codec for the original project's synthetic protocol only."""
from importlib.resources import files
import can
import cantools
from .telemetry import TelemetrySample


class SyntheticCodec:
    def __init__(self):
        self.database = cantools.database.load_string(
            files('can_lab').joinpath('data/synthetic.dbc').read_text(), database_format='dbc')

    def encode(self, message_name, signals):
        definition = self.database.get_message_by_name(message_name)
        return can.Message(arbitration_id=definition.frame_id,
                           data=definition.encode(signals, strict=True),
                           is_extended_id=False, check=True)

    def decode(self, message, *, time_basis='unix', source='synthetic-can'):
        if message.is_error_frame or message.is_remote_frame or message.is_fd:
            raise ValueError('expected a classical CAN data frame')
        if message.is_extended_id:
            raise ValueError('synthetic protocol uses standard identifiers')
        try:
            definition = self.database.get_message_by_frame_id(message.arbitration_id)
        except KeyError as error:
            raise ValueError(f'unknown synthetic CAN identifier: {message.arbitration_id:#x}') from error
        if message.dlc != definition.length or len(message.data) != definition.length:
            raise ValueError('incorrect frame length')
        values = definition.decode(message.data, decode_choices=False)
        return TelemetrySample(timestamp_s=message.timestamp, time_basis=time_basis,
                               source=source, **values)


def load_classical_dbc(text):
    """Load a strict, standard-ID classical integer-signal DBC for offline review.

    Existing SyntheticCodec is unchanged. This deliberately rejects untested
    extended/FD/multiplexed/float signal definitions instead of implying support.
    """
    try:
        database = cantools.database.load_string(text, database_format='dbc', strict=True)
    except Exception as error:
        raise ValueError(f'invalid DBC: {error}') from error
    if not database.messages:
        raise ValueError('DBC contains no messages')
    if len({message.frame_id for message in database.messages})!=len(database.messages):
        raise ValueError('duplicate DBC message identifiers are ambiguous')
    for message in database.messages:
        if len({s.name for s in message.signals})!=len(message.signals):
            raise ValueError('duplicate DBC signal names are ambiguous')
        if message.is_extended_frame or message.is_fd or message.length > 8:
            raise ValueError('only standard-ID classical CAN DBC messages are supported')
        if any(s.is_multiplexer or s.multiplexer_signal is not None or s.is_float for s in message.signals):
            raise ValueError('multiplexed and floating-point CAN signals are not supported')
    return database
