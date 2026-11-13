"""Common telemetry consumption must not require loading a CAN dependency."""
import subprocess
import sys


def test_common_schema_and_table_import_without_can():
    program = '''
import importlib.abc
import io
import sys
class NoCAN(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('can', 'cantools'):
            raise ImportError('CAN dependencies deliberately unavailable')
sys.meta_path.insert(0, NoCAN())
from can_lab.telemetry import TelemetrySample
from can_lab.io import load_csv, export_json
samples = load_csv(io.StringIO('timestamp_s,speed_kmh\\n0,36\\n'))
assert samples[0].speed_kmh == 36
assert samples[0].soc_pct is None
output = io.StringIO()
export_json(samples, output)
assert '36.0' in output.getvalue()
'''
    subprocess.run([sys.executable, '-c', program], check=True)
