"""Engineering-oriented recorded telemetry view; shared diagnostics/replay APIs."""
from dataclasses import asdict
import hashlib
import io
from itertools import islice
import json
import math
import tempfile
import time
import altair as alt
import pandas as pd
import streamlit as st
from .diagnostics import calculate_power, iter_vehicle_dynamics
from .excel import load_xlsx
from .quality import QualityConfig, quality_summary, validate_recording
from .recorded_io import export_recording_json, export_annotated_csv, export_diagnostic_summary
from .recording import COLUMNS, DatasetProfile, numeric
from .replay import RecordingSource, Replay


def upload_digest(upload):
    digest = hashlib.sha256()
    position = upload.tell()
    upload.seek(0)
    while chunk := upload.read(1024 * 1024):
        digest.update(chunk)
    upload.seek(position)
    return digest.hexdigest()


def value_and_unit(recording, row, signal):
    spec = recording.metadata['signals'][signal]
    if spec['unit_status'] == 'unverified':
        return numeric(row.raw.get(spec['source_column'])), 'source units unverified'
    return row.values.get(signal), spec['canonical_unit']


def signal_label(recording, signal):
    spec = recording.metadata['signals'][signal]
    return f"{signal} ({spec['canonical_unit'] if spec['unit_status'] != 'unverified' else 'source units UNVERIFIED'})"


def render_chart(recording, signal, *, title=None, derived=False):
    rows = recording.observations
    # Bounded display copy, never a full-workbook dataframe. Diagnostics use all rows.
    stride = max(1, math.ceil(len(rows) / 2000))
    selected = range(0, len(rows), stride)
    data = []
    for index in selected:
        row = rows[index]
        value = row.derived.get(signal, {}).get('value') if derived else value_and_unit(recording, row, signal)[0]
        issues = row.derived.get(signal, {}).get('quality', []) if derived else row.quality.get(signal, [])
        statuses = {issue['status'] for issue in issues}
        quality = 'MISSING' if value is None else ('SUSPICIOUS' if statuses - {'VALID'} else 'VALID')
        data.append({'timestamp_s': row.timestamp_s, 'row_number': row.row_number,
                     'value': value, 'quality': quality})
    frame = pd.DataFrame(data)
    st.subheader(title or signal_label(recording, signal))
    if not frame['value'].notna().any():
        st.caption('No usable numeric values. Raw cells remain available in the preview and exports.')
        return
    use_time = all(row.timestamp_s is not None for row in rows)
    x = 'timestamp_s' if use_time else 'row_number'
    extent = [min(frame[x]), max(frame[x])]
    x_encoding = alt.X(f'{x}:Q', scale=alt.Scale(domain=extent), title='Recording time (s)' if use_time else 'Original worksheet row (time unavailable)')
    base = alt.Chart(frame).encode(x=x_encoding, y=alt.Y('value:Q', title='kW, original current polarity' if derived else signal_label(recording, signal)))
    chart = (base.mark_line().encode(order='row_number:Q') +
             base.mark_point(size=25).encode(color=alt.Color('quality:N', scale=alt.Scale(
                 domain=['VALID', 'SUSPICIOUS', 'MISSING'], range=['#197b53', '#d87800', '#999999'])),
                 tooltip=['row_number', 'timestamp_s', 'value', 'quality']))
    st.altair_chart(chart, width='stretch')
    if stride > 1:
        st.caption(f'Display sampled every {stride} rows (maximum 2000 points). All rows are validated/exported; small anomalies may be absent from sampled plots.')


@st.fragment(run_every=0.25)
def replay_controls():
    replay = st.session_state.get('_ev_replay')
    if replay is None:
        return
    speed = st.selectbox('Playback speed', [0.25, 0.5, 1.0, 2.0, 5.0, 10.0], index=2, key='ev_playback_speed')
    now = time.monotonic()
    if speed != replay.speed:
        replay.set_speed(speed, now)
    play, pause, reset = st.columns(3)
    if play.button('Play', disabled=replay.finished, key='ev_play'):
        replay.play(now)
    if pause.button('Pause', key='ev_pause'):
        replay.pause(now)
    if reset.button('Reset', key='ev_reset'):
        replay.reset()
        replay.set_speed(speed, now)
    replay.advance(now)
    row = replay.current
    st.caption(f"{'Finished' if replay.finished else 'Playing' if replay.playing else 'Paused'} · original worksheet row {row.row_number} · recording timestamp {row.timestamp_s:g} s")
    columns = st.columns(4)
    recording = replay.source.recording
    for column, signal in zip(columns, ('speed_kmh', 'battery_voltage_v', 'battery_current_measured_a', 'soc_pct')):
        value, unit = value_and_unit(recording, row, signal)
        column.metric(signal, f'{value:g} {unit}' if value is not None else 'Missing')
    st.caption('Recorded-data replay only. No CAN identifiers or synthetic OEM frames are generated.')


def render_real_world():
    st.caption('Imported decoded measurements · Excel is not raw CAN · source units and signal definitions require documentation.')
    upload = st.file_uploader('Upload vehicle#1.xlsx or a compatible workbook', type=['xlsx'], key='ev_workbook')
    with st.expander('Source profile and quality thresholds', expanded=False):
        st.caption('Defaults do not assume numeric timestamps, units, charging codes, or current polarity. '
                   'Declare units only after inspecting your source documentation; declarations are retained as user-provided metadata.')
        dataset_id = st.text_input('Dataset identifier / edition', value=DatasetProfile().dataset_id)
        sheet = st.text_input('Worksheet (blank selects the first sheet)', value='')
        time_unit = st.selectbox('Timestamp representation', ['datetime', 's', 'ms', 'us'])
        time_basis = st.selectbox('Normalized timestamp basis', ['relative', 'unix'])
        declared_units = st.checkbox('Declare source units as km/h, km, V, A, %, V/cell and degC', value=False)
        convention = st.selectbox('Documented current convention', ['unknown', 'positive_discharge', 'positive_charge'])
        reference = st.text_input('Unit/sign documentation reference (if available)', value='')
        profile_upload = st.file_uploader('Optional JSON source profile (overrides controls)', type=['json'], key='ev_profile')
        config_text = st.text_area('Optional QualityConfig overrides as JSON', value='', help='For example: {"flatline_min_samples": 60, "expected_interval_s": 1}')
        max_rows = st.number_input('Maximum workbook observations (explicit safety limit)', min_value=1, max_value=2_000_000, value=250_000, step=1000)
    if upload is None:
        st.info('No workbook required at startup. Load a local .xlsx; real vehicle#1.xlsx is not bundled. '
                'A reproducible synthetic example can be generated with python examples/make_ev_fixture.py /tmp/synthetic-ev.xlsx.')
        return
    try:
        units = {column: unit for column, (_, unit) in COLUMNS.items() if unit is not None} if declared_units else {}
        profile = DatasetProfile(dataset_id=dataset_id, units=units, time_unit=time_unit,
                                 time_basis=time_basis, current_convention=convention, reference=reference)
        if profile_upload is not None:
            profile = DatasetProfile(**json.loads(profile_upload.getvalue()))
        config = QualityConfig(**json.loads(config_text)) if config_text.strip() else QualityConfig()
        key = (upload_digest(upload), upload.name, sheet, max_rows,
               json.dumps(asdict(profile), sort_keys=True), json.dumps(asdict(config), sort_keys=True))
        if st.session_state.get('_ev_recording_key') != key:
            recording = load_xlsx(upload, profile=profile, sheet=sheet or None, max_rows=int(max_rows), filename=upload.name)
            validate_recording(recording, config)
            calculate_power(recording)
            st.session_state['_ev_recording_key'] = key
            st.session_state['_ev_recording'] = recording
            try:
                st.session_state['_ev_replay'] = Replay(RecordingSource(recording))
                st.session_state['_ev_replay_error'] = None
            except ValueError as error:
                st.session_state['_ev_replay'] = None
                st.session_state['_ev_replay_error'] = str(error)
        recording = st.session_state['_ev_recording']
    except (ValueError, TypeError, KeyError, OSError) as error:
        st.error(f'Workbook import failed: {error}')
        return
    summary = quality_summary(recording)
    st.subheader('Overview')
    duration = recording.duration_s()
    metrics = [('Total observations', str(summary['total_observations'])),
               ('Recording duration', f'{duration:g} s' if duration is not None else 'Unverified/invalid time')]
    for signal, name in [('speed_kmh', 'Maximum vehicle speed'), ('battery_voltage_v', 'Battery voltage range'),
                         ('battery_current_measured_a', 'Battery current range'), ('soc_pct', 'SOC range'),
                         ('cell_temperature_max_c', 'Maximum-cell temperature range'), ('cell_temperature_min_c', 'Minimum-cell temperature range')]:
        values = [value_and_unit(recording, row, signal)[0] for row in recording.observations]
        values = [value for value in values if value is not None]
        unit = value_and_unit(recording, recording.observations[0], signal)[1]
        text = (f'{max(values):g}' if signal == 'speed_kmh' else f'{min(values):g} … {max(values):g}') + f' {unit}' if values else 'Missing'
        metrics.append((name, text))
    metrics.append(('Data quality', f"{summary['suspicious_observations']} suspicious / {summary['missing_observations']} with missing signals"))
    for start in range(0, len(metrics), 3):
        for column, (name, value) in zip(st.columns(3), metrics[start:start + 3]):
            column.metric(name, value)
    st.caption('Ranges include suspicious numeric observations; they are not validated operating limits.')
    dynamics_tab, electrical_tab, thermal_tab, quality_tab, replay_tab, exports_tab = st.tabs([
        'Vehicle Dynamics', 'Battery Electrical Measurements', 'Battery Temperature', 'Data Quality', 'Recorded Replay', 'Exports & Source'])
    with dynamics_tab:
        render_chart(recording, 'speed_kmh')
        st.caption('Acceleration uses adjacent normalized speed/time pairs passing configured checks; duplicates, irregular timestamps and suspect inputs yield missing derivatives.')
        preview = pd.DataFrame(islice(iter_vehicle_dynamics(recording), 0, None, max(1, math.ceil(len(recording.observations) / 2000))))
        if preview['acceleration_m_s2'].notna().any():
            st.line_chart(preview, x='timestamp_s', y='acceleration_m_s2')
        st.dataframe(preview.head(200))
    with electrical_tab:
        for signal in ('battery_voltage_v', 'battery_current_measured_a', 'soc_pct'):
            render_chart(recording, signal)
        st.caption('All electrical signals share original observation timestamps. Charts never align unrelated rows or fill missing values.')
        render_chart(recording, 'signed_power_kw', title='Signed calculated electrical power (kW)', derived=True)
        powers = [row.derived['signed_power_kw']['value'] for row in recording.observations if row.derived['signed_power_kw']['value'] is not None]
        st.write(f'Calculated power range: {min(powers):g} … {max(powers):g} kW' if powers else 'Power unavailable: declare input units and inspect invalid voltage/current values.')
        st.caption('P = V × I / 1000. Original measured current polarity is retained. ' + recording.metadata['derived_signals']['signed_power_kw']['sign_interpretation'])
    with thermal_tab:
        for signal in ('cell_temperature_max_c', 'cell_temperature_min_c'):
            render_chart(recording, signal)
        st.caption('Orange points indicate flagged values, including configured -40 degC sentinels and abnormal max/min differences. Missing measurements are not fabricated.')
    with quality_tab:
        st.json({key: value for key, value in summary.items() if key != 'per_signal'})
        st.dataframe(pd.DataFrame([{'signal': signal, **stats['statuses'], 'reasons': json.dumps(stats['reasons'])}
                                  for signal, stats in summary['per_signal'].items()]).fillna(0))
        for warning in recording.metadata['warnings']:
            st.warning(warning)
        st.caption('Defaults are configurable research screening heuristics, not OEM safety limits. Missing optional signals are counted, not invented.')
        st.subheader('Flagged observations (first 200)')
        flagged = []
        for row in recording.observations:
            if row.quality:
                flagged.append({'row': row.row_number, 'original_time': json.dumps(row.raw.get('time')), 'quality': json.dumps(row.quality)})
                if len(flagged) >= 200:
                    break
        st.dataframe(pd.DataFrame(flagged))
    with replay_tab:
        if st.session_state.get('_ev_replay_error'):
            st.warning(st.session_state['_ev_replay_error'])
        replay_controls()
    with exports_tab:
        st.json(recording.metadata)
        st.dataframe(pd.DataFrame([{'row': row.row_number, **{key: json.dumps(value) for key, value in row.raw.items()}}
                                  for row in recording.observations[:200]]))
        diagnostic = io.StringIO()
        export_diagnostic_summary(recording, diagnostic)
        st.download_button('Download diagnostic summary JSON', diagnostic.getvalue(), file_name='diagnostics.json', mime='application/json')
        if st.button('Prepare annotated exports (all observations)', key='ev_prepare_exports'):
            for name, exporter, mime in [('json', export_recording_json, 'application/json'), ('csv', export_annotated_csv, 'text/csv')]:
                with tempfile.TemporaryFile(mode='w+', encoding='utf-8', newline='') as output:
                    exporter(recording, output)
                    output.seek(0)
                    st.download_button(f'Download quality-annotated {name.upper()}', output, file_name=f'recorded-telemetry.{name}', mime=mime)
        st.caption('Exports preserve raw timestamps/cells, source column names, dataset ID, original and normalized units, quality flags and power definitions. No rows are silently dropped.')
