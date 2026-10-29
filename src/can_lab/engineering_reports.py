"""Machine-readable and human-readable reports without PDF/browser dependencies."""
import csv
import json
from .engineering import numeric_range


def build_report(recording,analysis):
    rows=recording.observations
    voltage_flags={}; temperature_flags={}
    for point in analysis.cells:
        for target,issues in ((voltage_flags,point.voltage_quality),(temperature_flags,point.temperature_quality)):
            for issue in set(issues):target[issue]=target.get(issue,0)+1
    return {
        'schema':'can-lab-engineering-report-1','software_version':'0.3.0',
        'provenance':recording.metadata,'configuration':analysis.configuration,
        'measurement_coverage':{'observations':len(rows),
            'normalized_signals':{key:sum(row.values.get(key) is not None for row in rows) for key in recording.signals},
            'policy':'Raw observations retained in recording exports; normalized nulls can mean unverified units, not missing raw data.'},
        'recording':{'duration_s_including_gaps':recording.duration_s(),'possible_sessions':len(analysis.sessions)},
        'vehicle_dynamics':{'acceleration_m_s2':numeric_range(p.acceleration_m_s2 for p in analysis.operating),
            'definition':'Backward derivative of causal trailing-median speed / 3.6 / actual elapsed seconds. Reset at boundaries, unusable samples and configured long intervals.',
            'confidence':'Dynamic states are inferred threshold candidates; source-reported charging codes remain distinct.'},
        'battery_electrical':analysis.electrical,'energy':analysis.energy,
        'cell_diagnostics':{'voltage_spread_v':numeric_range(p.voltage_spread_v for p in analysis.cells),
            'temperature_spread_c':numeric_range(p.temperature_spread_c for p in analysis.cells),
            'voltage_flags':voltage_flags,'temperature_flags':temperature_flags,
            'definitions':{'voltage_spread_v':'normalized cell max V - min V',
                           'temperature_spread_c':'normalized cell max degC - min degC'},
            'policy':'Ranges include quality-annotated values; zeros, negative spreads and sentinel candidates are measurement anomalies, not confirmed cell defects.'},
        'quality':analysis.quality,'sessions':analysis.sessions,'limitations':analysis.uncertainties,
        'data_categories':{'measured':'original workbook cells in source recording, same-row electrical pairs',
            'derived':'power, speed derivative, spreads, integrals, descriptive statistics',
            'inferred':'dynamic operating candidates and possible sessions; yearless time when selected',
            'source_reported':'status codes with explicit profile definitions',
            'unverified':'see source metadata, sign convention, units, time provenance and limitations'},
    }


def export_engineering_json(recording,analysis,stream):
    json.dump(build_report(recording,analysis),stream,indent=2,allow_nan=False)
    stream.write('\n')


def _text(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def export_engineering_markdown(recording,analysis,stream):
    report=build_report(recording,analysis)
    energy=analysis.energy
    stream.write('# Virtual ECU & CAN Lab — Engineering Report\n\n')
    stream.write(f"Dataset: {_text(recording.metadata['profile']['dataset_id'])}\n\n")
    stream.write(f"Source file: {_text(recording.metadata['source_filename'])}; SHA-256: `{recording.metadata['sha256']}`.\n\n")
    stream.write(f"Observations: {len(recording.observations)}. Possible sessions: {len(analysis.sessions)}. Recording span including gaps: {recording.duration_s()} s.\n\n")
    stream.write('## Provenance and interpretation\n\n')
    stream.write(f"Time: {_text(recording.metadata.get('time_interpretation_status'))}; current convention: {_text(recording.metadata['profile']['current_convention'])}.\n\n")
    stream.write('## Electrical and signed energy\n\n')
    for key in ('signed_net_kwh','positive_signed_kwh','negative_signed_kwh','absolute_throughput_kwh','included_intervals','excluded_intervals','included_duration_s','qualified_signed_kwh_per_km'):
        stream.write(f'- {key}: {energy[key]}\n')
    stream.write('\nSigned components retain measured polarity, not charging/discharging labels. This is accepted-interval energy, not verified vehicle efficiency.\n\n')
    stream.write('## Possible session overview\n\n| Session | Rows | Duration s | Max km/h | Signed kWh | Excluded intervals |\n| --- | --- | --- | --- | --- | --- |\n')
    for session in analysis.sessions:
        stream.write(f"| {session['session_id']} | {session['observations']} | {session['duration_s']} | {session['speed_kmh']['max']} | {session['energy']['signed_net_kwh']:.6g} | {session['energy']['excluded_intervals']} |\n")
    stream.write('\n## Cell and quality diagnostics\n\n')
    stream.write(f"- Cell-voltage spread range (annotated): {report['cell_diagnostics']['voltage_spread_v']}\n")
    stream.write(f"- Cell-temperature spread range (annotated): {report['cell_diagnostics']['temperature_spread_c']}\n")
    for key,value in analysis.quality['dimensions'].items():
        if key not in ('per_signal','policy'):
            stream.write(f'- {key}: {value}\n')
    stream.write('\nCounts are independent and may overlap. Metadata warnings alone do not imply physical invalidity.\n\n')
    stream.write('## Configuration and source references\n\n```json\n')
    stream.write(json.dumps({'configuration':analysis.configuration,'profile':recording.metadata['profile']},indent=2,allow_nan=False))
    stream.write('\n```\n\n## Engineering limitations\n\n')
    for limitation in analysis.uncertainties:stream.write('- '+limitation+'\n')
    stream.write('\nDetailed per-session ranges, candidate state counts, charging-code intervals, voltage response and quality coverage are in the companion JSON report.\n')


def iter_features(recording,analysis,indices=None):
    indices=range(len(recording.observations)) if indices is None else indices
    for i in indices:
        row=recording.observations[i];state=analysis.operating[i];cell=analysis.cells[i]
        yield {'row_number':row.row_number,'timestamp_s':row.timestamp_s,'raw_time':row.raw.get('time'),
               'speed_kmh':row.values.get('speed_kmh'),'smoothed_speed_kmh':state.smoothed_speed_kmh,
               'acceleration_m_s2':state.acceleration_m_s2,'operating_candidates':list(state.candidates),
               'source_reported_state':state.source_reported_state,'state_verification':state.verification,
               'state_warnings':list(state.warnings),'battery_voltage_v':row.values.get('battery_voltage_v'),
               'battery_current_measured_a':row.values.get('battery_current_measured_a'),
               'soc_pct':row.values.get('soc_pct'),'signed_power_kw':row.derived['signed_power_kw']['value'],
               'power_quality':row.derived['signed_power_kw']['quality'],
               'cell_voltage_spread_v':cell.voltage_spread_v,'cell_temperature_spread_c':cell.temperature_spread_c,
               'max_temperature_rate_c_s':cell.max_temperature_rate_c_s,'min_temperature_rate_c_s':cell.min_temperature_rate_c_s,
               'cell_voltage_quality':list(cell.voltage_quality),'cell_temperature_quality':list(cell.temperature_quality)}


def export_engineering_csv(recording,analysis,stream):
    stream.write('# can-lab-engineering-features-1 metadata='+json.dumps({'source':recording.metadata,'engineering_configuration':analysis.configuration,'limitations':analysis.uncertainties},allow_nan=False)+'\n')
    rows=iter_features(recording,analysis)
    first=next(rows,None)
    if first is None:raise ValueError('no engineering observations')
    writer=csv.DictWriter(stream,fieldnames=list(first));writer.writeheader()
    def write(row):
        # JSON-encode strings/structures (including original timestamps), so raw
        # formula-like text cannot become executable spreadsheet formulas.
        writer.writerow({key:json.dumps(value,allow_nan=False) if isinstance(value,(str,dict,list)) or key=='raw_time' else value for key,value in row.items()})
    write(first)
    for row in rows:write(row)
