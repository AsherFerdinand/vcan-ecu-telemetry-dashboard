"""Engineering-oriented recorded telemetry view; shared diagnostics/replay APIs."""
from dataclasses import asdict
import hashlib
from importlib.resources import files
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
from .recording_plots import prepare_signal_plot
from .recording_review import inspect_timestamps, anomaly_report
from .engineering import EngineeringConfig, analyze_engineering
from .engineering_dashboard import feature_frame, render_dynamics, render_electrical, render_health, render_sessions, render_reports


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


def chart_for_signal(recording, signal, indices, *, derived=False, title=None):
    cache = st.session_state.setdefault('_ev_plot_cache', {})
    cache_key = (signal, derived)
    if cache_key not in cache:
        cache[cache_key] = prepare_signal_plot(recording, indices, signal, derived=derived)
    prepared = cache[cache_key]
    frame = pd.DataFrame(prepared['data'])
    if frame.empty or not frame['value'].notna().any():
        return None
    inferred = recording.metadata.get('time_interpretation_status') == 'inferred_yearless_encoding'
    x_title = ('Elapsed recording seconds (INFERRED MDDHHMMSS; year unknown)' if inferred else 'Recording seconds (profile-declared time)') if prepared['use_time'] else 'Worksheet row index — NOT time'
    base = alt.Chart(frame).encode(x=alt.X('x:Q', scale=alt.Scale(domain=prepared['domain']), title=x_title),
        y=alt.Y('value:Q', title=title or ('Signed kW' if derived else signal_label(recording, signal))),
        tooltip=['row_number', 'raw_time', 'value', 'quality', 'flags'])
    points = base.mark_point(size=20).encode(color=alt.Color('quality:N', scale=alt.Scale(
        domain=['NUMERIC', 'PHYSICALLY_SUSPICIOUS', 'MISSING'], range=['#197b53', '#d87800', '#999999'])))
    # Row-index fallback cannot establish session continuity: show points only.
    if prepared['use_time']:
        return base.mark_line().encode(detail='group:N', order='row_number:Q') + points
    return points


def render_chart(recording, signal, *, title=None, derived=False):
    indices = st.session_state.get('_ev_plot_indices', list(range(len(recording.observations))))
    st.subheader(title or signal_label(recording, signal))
    chart = chart_for_signal(recording, signal, indices, derived=derived, title=title)
    if chart is None:
        st.caption('No usable numeric values in the selected interval. Original raw cells remain available.')
    else:
        st.altair_chart(chart, width='stretch')


def plot_window(recording):
    rows = recording.observations
    boundaries = recording.metadata.get('recording_boundaries', [])
    starts = [0] + [item['index'] for item in boundaries]
    if st.session_state.get('ev_segment',-1) not in [-1]+list(range(len(starts))):
        st.session_state['ev_segment']=-1
    segment = st.selectbox('Possible recording segment', [-1] + list(range(len(starts))),
        format_func=lambda value: 'All segments (lines remain separated)' if value == -1 else f'Possible segment {value + 1}', key='ev_segment')
    first = starts[segment] if segment >= 0 else 0
    last = (starts[segment + 1] - 1 if segment + 1 < len(starts) else len(rows)-1) if segment >= 0 else len(rows)-1
    if first == last:
        lower, upper = rows[first].row_number, rows[last].row_number
    else:
        lower, upper = st.slider('Worksheet row interval (shared by all charts)', rows[first].row_number, rows[last].row_number,
                                (rows[first].row_number, rows[last].row_number))
    indices = [i for i in range(first, last + 1) if lower <= rows[i].row_number <= upper]
    if indices and all(rows[i].timestamp_s is not None for i in indices):
        low, high = min(rows[i].timestamp_s for i in indices), max(rows[i].timestamp_s for i in indices)
        if low < high:
            left, right = st.slider('Recording seconds interval (shared by all charts)', float(low), float(high), (float(low), float(high)))
            indices = [i for i in indices if left <= rows[i].timestamp_s <= right]
        status = recording.metadata.get('time_interpretation_status', 'profile_declared')
        st.caption(f'Time axis: {status}. {len(boundaries)} possible boundaries; boundaries are heuristics, not verified driving sessions.')
    else:
        st.warning('UNVERIFIED TIME: worksheet-row fallback is NOT elapsed time. Plots use points only; raw timestamps are retained. Select a documented representation or the explicitly inferred MDDHHMMSS parser when supported by the recording.')
    st.caption('Shared interval controls synchronize all charts. Display is limited to 2000 points per signal, prioritizing selected anomaly points; zoom in for detail. Full data remains in diagnostics and exports.')
    st.session_state['_ev_plot_indices'] = indices
    return indices


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
    analysis = st.session_state.get('_ev_engineering')
    if analysis is not None:
        state = analysis.operating[max(0, replay.cursor-1)]
        extra = st.columns(3)
        extra[0].metric('Current operating candidates', ', '.join(state.candidates))
        power = row.derived.get('signed_power_kw', {}).get('value')
        extra[1].metric('Current signed power', f'{power:g} kW' if power is not None else 'Unavailable')
        temperature = row.values.get('cell_temperature_max_c')
        extra[2].metric('Current maximum-cell temperature', f'{temperature:g} degC' if temperature is not None else 'Unverified/missing')
        st.caption('State evidence: ' + state.verification + '; source-reported mode: ' + str(state.source_reported_state))
    st.caption('Recorded-data replay only. No CAN identifiers or synthetic OEM frames are generated.')


def render_real_world():
    st.caption('Imported decoded measurements · Excel is not raw CAN · source units and signal definitions require documentation.')
    upload = st.file_uploader('Upload vehicle#1.xlsx or a compatible workbook', type=['xlsx'], key='ev_workbook')
    with st.expander('Source profile and quality thresholds', expanded=False):
        st.caption('Defaults do not assume numeric timestamps, units, charging codes, or current polarity. '
                   'Declare units only after inspecting your source documentation; declarations are retained as user-provided metadata.')
        dataset_id = st.text_input('Dataset identifier / edition', value=DatasetProfile().dataset_id)
        sheet = st.text_input('Worksheet (blank selects the first sheet)', value='')
        time_unit = st.selectbox('Timestamp representation', ['datetime', 's', 'ms', 'us', 'MDDHHMMSS'])
        time_basis = st.selectbox('Normalized timestamp basis', ['relative', 'unix'])
        declared_units = st.checkbox('Declare source units as km/h, km, V, A, %, V/cell and degC', value=False)
        source_profile = st.checkbox('Use source-reviewed SCUT profile (timestamp encoding remains inferred)', value=False, help='Overrides unit/time/status controls using the pinned upstream README. SOC scale and current polarity remain unknown.')
        convention = st.selectbox('Documented current convention', ['unknown', 'positive_discharge', 'positive_charge'])
        current_reference = st.text_input('Current-polarity source reference (required for regeneration candidates)', value='')
        reference = st.text_input('Unit/sign documentation reference (if available)', value='')
        profile_upload = st.file_uploader('Optional JSON source profile (overrides controls)', type=['json'], key='ev_profile')
        config_text = st.text_area('Optional QualityConfig overrides as JSON', value='', help='For example: {"flatline_min_samples": 60, "expected_interval_s": 1}')
        engineering_text = st.text_area('Engineering thresholds as JSON (v0.3)', value='', help='Sections: operating, energy, cells. Example: {"operating": {"smoothing_samples": 3}, "energy": {"max_interval_s": 30}}')
        max_rows = st.number_input('Maximum workbook observations (explicit safety limit)', min_value=1, max_value=2_000_000, value=250_000, step=1000)
    if upload is None:
        st.info('No workbook required at startup. Load a local .xlsx; real vehicle#1.xlsx is not bundled. '
                'A reproducible synthetic example can be generated with python examples/make_ev_fixture.py /tmp/synthetic-ev.xlsx.')
        return
    try:
        units = {column: unit for column, (_, unit) in COLUMNS.items() if unit is not None} if declared_units else {}
        profile = DatasetProfile(dataset_id=dataset_id, units=units, time_unit=time_unit,
                                 time_basis=time_basis, current_convention=convention, current_reference=current_reference, reference=reference)
        if source_profile:
            profile = DatasetProfile(**json.loads(files('can_lab').joinpath('data/translab_scut_vehicle1_review.json').read_text()))
        if profile_upload is not None:
            profile = DatasetProfile(**json.loads(profile_upload.getvalue()))
        config = QualityConfig(**json.loads(config_text)) if config_text.strip() else QualityConfig(expected_interval_s=10) if source_profile else QualityConfig()
        key = ('review-v3', upload_digest(upload), upload.name, sheet, max_rows,
               json.dumps(asdict(profile), sort_keys=True), json.dumps(asdict(config), sort_keys=True))
        if st.session_state.get('_ev_recording_key') != key:
            recording = load_xlsx(upload, profile=profile, sheet=sheet or None, max_rows=int(max_rows), filename=upload.name)
            validate_recording(recording, config)
            calculate_power(recording)
            st.session_state['_ev_quality_summary'] = quality_summary(recording)
            st.session_state['_ev_timestamp_report'] = inspect_timestamps(recording)
            st.session_state['_ev_anomaly_report'] = anomaly_report(recording)
            diagnostic = io.StringIO()
            export_diagnostic_summary(recording, diagnostic, summary=st.session_state['_ev_quality_summary'],
                timestamp_evidence=st.session_state['_ev_timestamp_report'], anomaly_review=st.session_state['_ev_anomaly_report'])
            st.session_state['_ev_diagnostic_json'] = diagnostic.getvalue()
            st.session_state['_ev_recording_key'] = key
            st.session_state['_ev_recording'] = recording
            try:
                st.session_state['_ev_replay'] = Replay(RecordingSource(recording))
                st.session_state['_ev_replay_error'] = None
            except ValueError as error:
                st.session_state['_ev_replay'] = None
                st.session_state['_ev_replay_error'] = str(error)
        recording = st.session_state['_ev_recording']
        engineering_config = EngineeringConfig.from_dict(json.loads(engineering_text)) if engineering_text.strip() else EngineeringConfig()
        engineering_key = ('v0.3', key, json.dumps(asdict(engineering_config), sort_keys=True))
        if st.session_state.get('_ev_engineering_key') != engineering_key:
            st.session_state['_ev_engineering'] = analyze_engineering(recording, engineering_config, quality=st.session_state['_ev_quality_summary'])
            st.session_state['_ev_engineering_key'] = engineering_key
        analysis = st.session_state['_ev_engineering']
    except (ValueError, TypeError, KeyError, OSError) as error:
        st.error(f'Workbook import failed: {error}')
        return
    summary = st.session_state['_ev_quality_summary']
    dimensions = summary['dimensions']
    st.subheader('Overview')
    duration = recording.duration_s()
    category_metrics = [
        ('Imported observations', 'imported_observations', 'All original rows; none removed.'),
        ('Numerically plausible observations', 'numerically_plausible_observations', 'Available finite measurements with no detected normalized range violation. Heuristic suspicion or missing fields may overlap. Does not establish units, complete physical screening, or sensor accuracy.'),
        ('Physically suspicious observations', 'physically_suspicious_observations', 'Configured physical checks or raw-value candidates, independent of unit metadata and clock issues.'),
        ('Metadata-unverified observations', 'metadata_unverified_observations', 'At least one unit, status code, current polarity or timestamp interpretation remains unverified. Does not imply physical invalidity.'),
        ('Timestamp-invalid observations', 'timestamp_invalid_observations', 'Invalid components, unusable values, duplicate or reversed clocks. Cadence anomalies are separate; unverified representation is not automatically invalid.'),
        ('Missing-data observations', 'missing_data_observations', 'At least one missing or nonnumeric field. Categories overlap.'),
    ]
    for start in range(0, len(category_metrics), 3):
        for column, (label, key, help_text) in zip(st.columns(3), category_metrics[start:start+3]):
            column.metric(label, dimensions[key], help=help_text)
    st.caption(f"Physical checks incomplete for {dimensions['physical_checks_incomplete_observations']} observations; time representation unverified for {dimensions['timestamp_unverified_observations']} observations; cadence/clock flags affect {dimensions['timestamp_anomaly_observations']} observations. Legacy conservative counts are retained in Data Quality.")
    metrics = [('Recording observations', str(summary['total_observations'])),
               ('Recording duration', f'{duration:g} s' if duration is not None else 'Unverified/invalid time')]
    for signal, name in [('speed_kmh', 'Maximum vehicle speed'), ('battery_voltage_v', 'Battery voltage range'),
                         ('battery_current_measured_a', 'Battery current range'), ('soc_pct', 'SOC range'),
                         ('cell_temperature_max_c', 'Maximum-cell temperature range'), ('cell_temperature_min_c', 'Minimum-cell temperature range')]:
        values = [value_and_unit(recording, row, signal)[0] for row in recording.observations]
        values = [value for value in values if value is not None]
        unit = value_and_unit(recording, recording.observations[0], signal)[1]
        text = (f'{max(values):g}' if signal == 'speed_kmh' else f'{min(values):g} … {max(values):g}') + f' {unit}' if values else 'Missing'
        metrics.append((name, text))

    with st.expander('Signal ranges and recording duration', expanded=False):
        for start in range(0, len(metrics), 3):
            for column, (name, value) in zip(st.columns(3), metrics[start:start + 3]):
                column.metric(name, value)
    st.caption('Physical-suspicion counts include configurable flatline and jump heuristics, not proven faults. Constant temperatures can be legitimate. Ranges include flagged values.')
    indices = plot_window(recording)
    st.session_state['_ev_plot_cache'] = {}
    with st.expander('Synchronized signal overview', expanded=True):
        charts = [chart_for_signal(recording, signal, indices) for signal in ('speed_kmh', 'battery_voltage_v', 'battery_current_measured_a', 'soc_pct', 'cell_temperature_max_c', 'cell_temperature_min_c')]
        charts = [chart for chart in charts if chart is not None]
        if charts:
            st.altair_chart(alt.vconcat(*charts).resolve_scale(x='shared', y='independent'), width='stretch')
    engineering_frame = feature_frame(recording, analysis, indices)
    st.caption(f'v0.3 engineering analysis · {len(analysis.sessions)} possible sessions · candidates, signed integrals and measurement anomalies are not verified battery health or vehicle efficiency.')
    dynamics_tab, electrical_tab, thermal_tab, sessions_tab, quality_tab, replay_tab, exports_tab = st.tabs([
        'Vehicle Dynamics', 'Battery Electrical', 'Battery Health Indicators', 'Session Explorer', 'Diagnostics', 'Recorded Replay', 'Exports & Source'])
    with dynamics_tab:
        render_chart(recording, 'speed_kmh')
        st.caption('Acceleration uses adjacent normalized speed/time pairs passing configured checks; duplicates, irregular timestamps and suspect inputs yield missing derivatives.')
        selected_indices = set(indices)
        preview = pd.DataFrame(islice((item for i, item in enumerate(iter_vehicle_dynamics(recording)) if i in selected_indices), 0, None, max(1, math.ceil(len(indices) / 2000))))
        st.dataframe(preview.head(200))
        render_dynamics(recording, analysis, engineering_frame)
    with electrical_tab:
        for signal in ('battery_voltage_v', 'battery_current_measured_a', 'soc_pct'):
            render_chart(recording, signal)
        st.caption('All electrical signals share original observation timestamps. Charts never align unrelated rows or fill missing values.')
        render_chart(recording, 'signed_power_kw', title='Signed calculated electrical power (kW)', derived=True)
        powers = [row.derived['signed_power_kw']['value'] for row in recording.observations if row.derived['signed_power_kw']['value'] is not None]
        st.write(f'Calculated power range: {min(powers):g} … {max(powers):g} kW' if powers else 'Power unavailable: declare input units and inspect invalid voltage/current values.')
        st.caption('P = V × I / 1000. Original measured current polarity is retained. ' + recording.metadata['derived_signals']['signed_power_kw']['sign_interpretation'])
        render_electrical(recording, analysis, engineering_frame)
    with thermal_tab:
        for signal in ('cell_temperature_max_c', 'cell_temperature_min_c'):
            render_chart(recording, signal)
        st.caption('Orange points show physical-screening issues or raw-value candidates. A raw -40 with unverified units is a candidate, not a verified -40 degC measurement. No values are deleted.')
        render_health(recording, analysis, engineering_frame)
    with sessions_tab:
        render_sessions(recording, analysis)
    with quality_tab:
        st.subheader('Timestamp representation evidence')
        st.json(st.session_state['_ev_timestamp_report'])
        st.subheader('Possible recording boundaries')
        st.dataframe(pd.DataFrame(recording.metadata.get('recording_boundaries', [])))
        st.subheader('Physical anomalies and raw-step review')
        st.json(st.session_state['_ev_anomaly_report'])
        st.subheader('Independent quality dimensions')
        st.json(dimensions)
        st.subheader('Legacy conservative flags (include metadata and time)')
        st.json({key: value for key, value in summary.items() if key not in ('per_signal', 'dimensions')})
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
        render_reports(recording, analysis)
    with replay_tab:
        if st.session_state.get('_ev_replay_error'):
            st.warning(st.session_state['_ev_replay_error'])
        replay_controls()
    with exports_tab:
        st.json(recording.metadata)
        st.dataframe(pd.DataFrame([{'row': row.row_number, **{key: json.dumps(value) for key, value in row.raw.items()}}
                                  for row in recording.observations[:200]]))
        st.download_button('Download diagnostic summary JSON', st.session_state['_ev_diagnostic_json'], file_name='diagnostics.json', mime='application/json')
        if st.button('Prepare annotated exports (all observations)', key='ev_prepare_exports'):
            for name, exporter, mime in [('json', export_recording_json, 'application/json'), ('csv', export_annotated_csv, 'text/csv')]:
                with tempfile.TemporaryFile(mode='w+', encoding='utf-8', newline='') as output:
                    exporter(recording, output)
                    output.seek(0)
                    st.download_button(f'Download quality-annotated {name.upper()}', output, file_name=f'recorded-telemetry.{name}', mime=mime)
        st.caption('Exports preserve raw timestamps/cells, source column names, dataset ID, original and normalized units, quality flags and power definitions. No rows are silently dropped.')
