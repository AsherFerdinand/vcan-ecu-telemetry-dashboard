from pathlib import Path
import pytest
pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest

DASHBOARD=Path(__file__).parents[1]/'src/can_lab/dashboard.py'


def raw_app():
    app=AppTest.from_file(str(DASHBOARD)).run()
    app.selectbox[0].select('Raw CAN Investigation (v0.4 foundation)').run()
    return app


def test_raw_can_workspace_without_external_dataset():
    app=raw_app()
    assert not app.exception and not app.error
    assert any('synthetic fixtures only' in entry.value for entry in app.warning)
    app.button(key='can_investigate').click().run()
    assert not app.exception and any('Provide both' in entry.value for entry in app.error)


def test_raw_can_synthetic_example_engineering_and_reports():
    app=raw_app()
    app.checkbox(key='can_example').check().run()
    app.button(key='can_investigate').click().run()
    assert not app.exception and not app.error
    result=app.session_state['_can_investigation']
    assert result.validation['passed']==5 and len(result.recording.observations)==4
    app.button(key='can_engineering').click().run()
    assert not app.exception
    assert app.session_state['_can_engineering'].energy['included_intervals']==0
    app.button(key='can_reports').click().run()
    assert not app.exception


def test_raw_can_bounded_preview_warns():
    app=raw_app()
    app.checkbox(key='can_example').check().run()
    app.number_input[0].set_value(1).run()
    app.button(key='can_investigate').click().run()
    assert not app.exception
    assert len(app.session_state['_can_investigation'].frames)==1
    assert any('Processing limit reached' in item.value for item in app.warning)
