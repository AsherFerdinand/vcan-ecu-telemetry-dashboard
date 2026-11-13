"""Phase 3 analysis assembly: states, electrical relationships, cells and sessions."""
from collections import Counter
from dataclasses import asdict, dataclass, field
from statistics import correlation, StatisticsError
from .cells import CellConfig, analyze_cells
from .diagnostics import calculate_power
from .energy import EnergyConfig, integrate_energy
from .engineering_common import boundary_indices, finite, source_status, usable
from .operating import OperatingConfig, analyze_operating_states
from .recording import numeric
from .quality import quality_summary, validate_recording


@dataclass
class EngineeringConfig:
    operating: OperatingConfig = field(default_factory=OperatingConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    cells: CellConfig = field(default_factory=CellConfig)
    power_histogram_bins: int = 20

    def __post_init__(self):
        if not isinstance(self.operating,OperatingConfig) or not isinstance(self.energy,EnergyConfig) or not isinstance(self.cells,CellConfig):
            raise ValueError('engineering sections require their typed configurations')
        if type(self.power_histogram_bins) is not int or not 1 <= self.power_histogram_bins <= 100:
            raise ValueError('power_histogram_bins must be between 1 and 100')

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data,dict) or set(data)-{'operating','energy','cells','power_histogram_bins'}:
            raise ValueError('unsupported engineering configuration fields')
        try:
            return cls(OperatingConfig(**data.get('operating',{})), EnergyConfig(**data.get('energy',{})),
                       CellConfig(**data.get('cells',{})), data.get('power_histogram_bins',20))
        except TypeError as error:
            raise ValueError('engineering configuration sections must contain supported threshold fields') from error


@dataclass
class EngineeringAnalysis:
    configuration: dict
    operating: list
    cells: list
    energy: dict
    electrical: dict
    sessions: list[dict]
    quality: dict
    uncertainties: list[str]


def numeric_range(values):
    values=[value for value in values if finite(value)]
    return {'min': min(values) if values else None,'max': max(values) if values else None,'count':len(values)}


def _histogram(values,bins):
    if not values:
        return []
    low,high=min(values),max(values)
    if low==high:
        return [{'lower_kw':low,'upper_kw':high,'count':len(values)}]
    width=(high-low)/bins
    counts=[0]*bins
    for value in values:
        counts[min(bins-1,int((value-low)/width))]+=1
    return [{'lower_kw':low+i*width,'upper_kw':low+(i+1)*width,'count':count} for i,count in enumerate(counts)]


def _relationship(rows,x,y):
    pairs=[(row.values.get(x),row.values.get(y)) for row in rows if usable(row,x) and usable(row,y)]
    coefficient=None
    if len(pairs)>=3:
        try: coefficient=correlation([p[0] for p in pairs],[p[1] for p in pairs])
        except StatisticsError: pass
    return {'pearson_r':coefficient,'paired_observations':len(pairs),
            'interpretation':'Same-row screened pairs; association only, not causation, internal resistance, or proof of voltage sag.'}


def _candidate_events(rows, operating, start, end):
    events=[]; beginning=None; previous_state=None
    for i in range(start,end+1):
        state=next((s for s in operating[i].candidates if s in ('acceleration','deceleration')),None) if i<end else None
        # A state restart at a derivative reset also prevents event bridging.
        if state!=previous_state:
            if beginning is not None:
                first,last=rows[beginning],rows[i-1]
                a,b=first.values.get('battery_voltage_v'),last.values.get('battery_voltage_v')
                events.append({'candidate':previous_state,'start_row':first.row_number,'end_row':last.row_number,
                    'start_timestamp_s':first.timestamp_s,'end_timestamp_s':last.timestamp_s,'observations':i-beginning,
                    'voltage_start_v':a,'voltage_end_v':b,
                    'voltage_change_v':b-a if usable(first,'battery_voltage_v') and usable(last,'battery_voltage_v') else None,
                    'interpretation':'Descriptive same-row response during an inferred event; not evidence of causal voltage sag or internal resistance.'})
            beginning=i if state is not None else None
        previous_state=state
    return events


def _session_summary(recording, operating, cells, start,end,identifier,config):
    rows=recording.observations
    selected=rows[start:end]
    times=[row.timestamp_s for row in selected]
    ordered=bool(times) and all(finite(t) for t in times) and all(b>=a for a,b in zip(times,times[1:]))
    distribution=Counter(state for point in operating[start:end] for state in point.candidates)
    status_counts=Counter(point.source_reported_state or 'unknown' for point in operating[start:end])
    flags=Counter(issue['status'] for row in selected for issues in row.quality.values() for issue in issues)
    states={}
    for state in ('acceleration','deceleration'):
        values=[row.values.get('battery_voltage_v') for row,point in zip(selected,operating[start:end])
                if state in point.candidates and usable(row,'battery_voltage_v')]
        states[state]=numeric_range(values)
    soc_first,soc_last=selected[0].values.get('soc_pct'),selected[-1].values.get('soc_pct')
    energy=integrate_energy(recording,config.energy,start=start,end=end)
    distance=None
    if ordered and all(usable(row,'odometer_km') for row in selected) and len(selected)>1:
        deltas=[b.values['odometer_km']-a.values['odometer_km'] for a,b in zip(selected,selected[1:])]
        if all(0<=d<=config.energy.max_distance_speed_kmh*(b.timestamp_s-a.timestamp_s)/3600 for d,a,b in zip(deltas,selected,selected[1:])):
            distance=selected[-1].values['odometer_km']-selected[0].values['odometer_km']
    raw_soc_first,raw_soc_last=numeric(selected[0].raw.get('bcell_soc')),numeric(selected[-1].raw.get('bcell_soc'))
    charging=[]; run_start=None
    for i in range(start,end+1):
        is_charging=i<end and 'charging' in operating[i].candidates
        if is_charging and run_start is None:run_start=i
        if not is_charging and run_start is not None:
            a,b=rows[run_start],rows[i-1]
            charging.append({'start_row':a.row_number,'end_row':b.row_number,'start_timestamp_s':a.timestamp_s,
                             'end_timestamp_s':b.timestamp_s,'observations':i-run_start,
                             'evidence':'source-reported charging-status code, not inferred from power/current sign'})
            run_start=None
    return {'session_id':identifier,'start_index':start,'end_index_exclusive':end,
            'start_row':selected[0].row_number,'end_row':selected[-1].row_number,
            'start_raw_timestamp':selected[0].raw.get('time'),'end_raw_timestamp':selected[-1].raw.get('time'),
            'start_timestamp_s':times[0],'end_timestamp_s':times[-1],
            'duration_s':times[-1]-times[0] if ordered else None,'observations':end-start,
            'segmentation_status':'possible_recording_segment_not_confirmed_trip',
            'speed_kmh':numeric_range(row.values.get('speed_kmh') for row in selected),
            'battery_voltage_v':numeric_range(row.values.get('battery_voltage_v') for row in selected),
            'battery_current_measured_a':numeric_range(row.values.get('battery_current_measured_a') for row in selected),
            'soc_pct':numeric_range(row.values.get('soc_pct') for row in selected),
            'soc_change_pct':soc_last-soc_first if usable(selected[0],'soc_pct') and usable(selected[-1],'soc_pct') else None,
            'soc_change_source_units':raw_soc_last-raw_soc_first if raw_soc_first is not None and raw_soc_last is not None else None,
            'distance_km':distance,'distance_status':'screened declared-unit odometer change; not inferred from speed or energy',
            'candidate_dynamics_events':_candidate_events(rows,operating,start,end),
            'soc_source_unit_status':recording.metadata['signals']['soc_pct']['unit_status'],
            'cell_temperature_c':numeric_range(row.values.get(key) for row in selected for key in ('cell_temperature_max_c','cell_temperature_min_c')),
            'voltage_spread_v':numeric_range(point.voltage_spread_v for point in cells[start:end]),
            'temperature_spread_c':numeric_range(point.temperature_spread_c for point in cells[start:end]),
            'candidate_state_counts':dict(distribution),'source_reported_status_counts':dict(status_counts),
            'state_count_policy':'Overlapping candidates per observation; counts are not duration percentages.',
            'voltage_during_candidate_states_v':states,'charging_intervals':charging,
            'quality_flag_counts':dict(flags),'flagged_observations':sum(bool(row.quality) for row in selected),
            'energy':energy}


def analyze_engineering(recording,config=None,*,quality=None):
    config=config or EngineeringConfig()
    if not recording.observations:
        raise ValueError('engineering analysis requires observations')
    if 'quality_configuration' not in recording.metadata:
        validate_recording(recording)
    calculate_power(recording)
    operating=analyze_operating_states(recording,config.operating)
    cells=analyze_cells(recording,config.cells)
    rows=recording.observations
    powers=[row.derived['signed_power_kw']['value'] for row in rows if finite(row.derived['signed_power_kw']['value'])]
    starts=[0]+sorted(i for i in boundary_indices(recording) if 0<i<len(rows))
    sessions=[_session_summary(recording,operating,cells,start, starts[i+1] if i+1<len(starts) else len(rows),i+1,config)
              for i,start in enumerate(starts)]
    electrical={'signed_power_kw':numeric_range(powers),'power_distribution':_histogram(powers,config.power_histogram_bins),
                'voltage_vs_current':_relationship(rows,'battery_current_measured_a','battery_voltage_v'),
                'voltage_vs_speed':_relationship(rows,'speed_kmh','battery_voltage_v'),
                'power_definition':'V * measured A / 1000; original measured polarity retained',
                'range_policy':'All finite calculated powers, including quality-annotated suspect inputs; see source input flags. Energy integration uses stricter interval screening.'}
    energy=integrate_energy(recording,config.energy)
    uncertainties=[
        'Operating-state dynamics and possible regeneration are inferred candidates, not confirmed driving/braking events.',
        'Charging labels require explicit source status definitions; reported mode is not proof of a physical charging event.',
        'Cell anomalies are measurement-screening hints, not confirmed battery defects or battery health/SOH estimates.',
        'Signed energy is over accepted intervals only; not total recording energy, verified efficiency, or an auxiliary-load-corrected consumption estimate.',
        'Relationships use same-row measurements and do not establish causation or battery internal resistance.',
        'Possible sessions come from recording boundaries, not verified trip identifiers.',
    ]
    if not energy['included_intervals']:
        uncertainties.append('No usable integration intervals: a zero accepted-interval integral does not establish zero energy consumption.')
    elif energy['qualified_signed_kwh_per_km'] is None:
        uncertainties.append('Complete screened odometer coverage or positive matched distance is unavailable: energy per distance is withheld. Confirm odometer scale, resolution and step semantics.')
    if recording.metadata.get('time_interpretation_status')=='inferred_yearless_encoding':
        uncertainties.append('Elapsed time uses inferred MDDHHMMSS encoding; recording year and timezone remain unknown.')
    if recording.metadata['profile']['current_convention']=='unknown':
        uncertainties.append('Current polarity unknown: no charge/discharge sign labels and no regenerative-braking candidates.')
    elif not recording.metadata['profile'].get('current_reference'):
        uncertainties.append('Current polarity declared without a dedicated source reference: regeneration is not assessed.')
    if recording.metadata['signals']['soc_pct']['unit_status']=='unverified':
        uncertainties.append('SOC scale unverified: raw SOC remains in source telemetry; no normalized SOC change is asserted.')
    return EngineeringAnalysis(asdict(config),operating,cells,energy,electrical,sessions,
                               quality if quality is not None and 'signed_power_kw' in quality.get('per_signal',{}) else quality_summary(recording),uncertainties)
