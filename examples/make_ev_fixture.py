"""Generate a clearly SYNTHETIC workbook and unit profile; no real vehicle data."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from openpyxl import Workbook


def make_fixture(path):
    path = Path(path)
    profile_path = path.with_suffix('.profile.json')
    if path.exists() or profile_path.exists():
        raise ValueError('refusing to overwrite an existing example')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Synthetic EV'
    sheet.append(['time', 'vhc_speed', 'charging_signal', 'vhc_totalMile', 'hv_voltage',
                  'hv_current', 'bcell_soc', 'bcell_maxVoltage', 'bcell_minVoltage',
                  'bcell_maxTemp', 'bcell_minTemp'])
    for i in range(60):
        sheet.append([datetime(2026, 1, 1) + timedelta(seconds=i),
                      max(0, 36 - abs(30 - i)), 0, 1000 + i * .002, 400, 10 + i / 10,
                      80 - i / 100, 4.1, 4.0, -40 if i == 10 else 26 + i / 100, 25])
    workbook.save(path)
    workbook.close()
    profile = {
        'dataset_id': 'synthetic-phase2-example-NOT-REAL-VEHICLE-DATA',
        'units': {'vhc_speed': 'km/h', 'vhc_totalMile': 'km', 'hv_voltage': 'V', 'hv_current': 'A',
                  'bcell_soc': '%', 'bcell_maxVoltage': 'V', 'bcell_minVoltage': 'V',
                  'bcell_maxTemp': 'degC', 'bcell_minTemp': 'degC'},
        'time_unit': 'datetime', 'time_basis': 'relative', 'current_convention': 'unknown',
        'reference': 'Handwritten synthetic fixture; these units are NOT verified for the public research dataset.',
    }
    profile_path.write_text(json.dumps(profile, indent=2) + '\n')
    return path, profile_path


if __name__ == '__main__':
    for result in make_fixture(sys.argv[1]):
        print(result)
