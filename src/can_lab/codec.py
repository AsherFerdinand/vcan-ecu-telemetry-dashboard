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
