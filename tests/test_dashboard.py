from pathlib import Path
from unittest.mock import patch
import pytest

pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).parents[1] / 'src/can_lab/dashboard.py'
FIXTURE = Path(__file__).parent / 'fixtures/synthetic.csv'


class Upload:
    name = 'synthetic.csv'
    def getvalue(self):
        return FIXTURE.read_bytes()


def test_dashboard_empty():
    app = AppTest.from_file(str(DASHBOARD)).run()
    assert not app.exception
    assert app.title[0].value == 'Automotive CAN & Telemetry Laboratory'


def test_dashboard_import():
    with patch('streamlit.file_uploader', return_value=Upload()):
        app = AppTest.from_file(str(DASHBOARD)).run()
    assert not app.exception
    assert not app.error
    assert len(app.dataframe[0].value) == 4
    assert app.multiselect[0].value == ['speed_kmh', 'rpm', 'battery_voltage_v']
