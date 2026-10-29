"""Run with: python -m streamlit run src/can_lab/dashboard.py"""
import io
import pandas as pd
import streamlit as st
from can_lab.io import load_csv, load_json, load_candump, export_csv, export_json
from can_lab.telemetry import SIGNALS

st.set_page_config(page_title='Automotive Telemetry Lab', layout='wide')
st.title('Automotive CAN & Telemetry Laboratory')
st.caption('Sparse observations in canonical units. No interpolation or forward filling. '
           'Synthetic CAN definitions are not vehicle-specific definitions.')
source = st.selectbox('Data Source', ['Virtual ECU Simulation', 'Imported CAN Log', 'Real-World EV Dataset'], key='data_source')
if source == 'Real-World EV Dataset':
    from can_lab.recorded_dashboard import render_real_world
    render_real_world()
    st.stop()
if source == 'Imported CAN Log':
    st.caption('Decoded CAN data using the verified synthetic DBC; no OEM vehicle definitions are implied.')
else:
    if st.button('Run virtual ECU sample', key='run_virtual_demo'):
        from can_lab.cli import demo
        st.session_state['_virtual_samples'] = demo(50)
upload = st.file_uploader('Upload canonical CSV/JSON or synthetic-protocol candump log' if source == 'Virtual ECU Simulation' else 'Upload synthetic-protocol candump log',
                          type=['csv', 'json', 'log'] if source == 'Virtual ECU Simulation' else ['log'])
basis = st.selectbox('Timestamp basis (must match the recording)', ['relative', 'unix'])
try:
    samples = None
    if upload is not None:
        suffix = upload.name.rsplit('.', 1)[-1].lower()
        if source == 'Imported CAN Log' and suffix != 'log':
            raise ValueError('Imported CAN Log expects a classical candump .log file')
        loader = {'csv': load_csv, 'json': load_json, 'log': load_candump}[suffix]
        samples = loader(io.StringIO(upload.getvalue().decode('utf-8-sig')), time_basis=basis)
        st.caption('Decoded CAN data (synthetic protocol)' if suffix == 'log' else 'Imported decoded telemetry; see per-observation source fields for provenance.')
    elif source == 'Virtual ECU Simulation':
        samples = st.session_state.get('_virtual_samples')
        if samples:
            st.caption('Simulated: original synthetic ECU through python-can virtual buses.')
    if samples:
        st.write(f'{len(samples)} samples; {sum(bool(s.quality_flags) for s in samples)} flagged')
        data = pd.DataFrame([sample.to_dict() for sample in samples])
        st.dataframe(data)
        available = [key for key in SIGNALS if data[key].notna().any()]
        selected = st.multiselect('Signals (separate axes preserve their units)', available, default=available[:3])
        for key in selected:
            st.subheader(key)
            st.line_chart(data[['timestamp_s', key]].dropna(), x='timestamp_s', y=key)
        for name, exporter in [('json', export_json), ('csv', export_csv)]:
            output = io.StringIO()
            exporter(samples, output)
            st.download_button(f'Download standardized {name.upper()}', output.getvalue(),
                               file_name=f'telemetry.{name}', mime='application/json' if name == 'json' else 'text/csv')
    else:
        st.info('Run the virtual ECU sample or use tests/fixtures/synthetic.csv to explore the explicitly synthetic example. '
                'Normalize vehicle-specific tables with can-lab import --profile, or select Real-World EV Dataset for Excel.')
except (ValueError, UnicodeError, KeyError) as error:
    st.error(str(error))
