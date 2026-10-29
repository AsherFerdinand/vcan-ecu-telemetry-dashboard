"""Bounded engineering views using the recorded workspace's shared selection."""
from collections import Counter
import math
import tempfile
import altair as alt
import pandas as pd
import streamlit as st
from .engineering_reports import export_engineering_json, export_engineering_markdown, export_engineering_csv, iter_features


def feature_frame(recording,analysis,indices):
    if not indices:
        return pd.DataFrame()
    stride=max(1,math.ceil(len(indices)/1500))
    sampled=indices[::stride]
    records=list(iter_features(recording,analysis,sampled))
    boundaries={b['index'] for b in recording.metadata.get('recording_boundaries',[])}
    group=0; previous=None; groups={}
    fields=('acceleration_m_s2','cell_voltage_spread_v','cell_temperature_spread_c','max_temperature_rate_c_s','min_temperature_rate_c_s')
    counters={key:0 for key in fields}; previous_missing={key:True for key in fields}
    wanted=set(sampled)
    for i in indices:
        if i in boundaries or previous is None or i!=previous+1:group+=1
        p,c=analysis.operating[i],analysis.cells[i]
        values=(p.acceleration_m_s2,c.voltage_spread_v,c.temperature_spread_c,c.max_temperature_rate_c_s,c.min_temperature_rate_c_s)
        for key,value in zip(fields,values):
            if previous_missing[key] or value is None or i in boundaries or previous is None or i!=previous+1:counters[key]+=1
            previous_missing[key]=value is None
        if i in wanted:groups[i]=(group,dict(counters))
        previous=i
    use_time=all(recording.observations[j].timestamp_s is not None for j in indices)
    for item,i in zip(records,sampled):
        item['candidate_label']=', '.join(item['operating_candidates'])
        item['group']=str(groups[i][0])
        for key in fields:item['group_'+key]=str(groups[i][1][key])
        item['x']=item['timestamp_s'] if use_time else item['row_number']
    for row in records:
        row['cell_voltage_screening']='ANNOTATED' if row['cell_voltage_quality'] else 'NO_FLAG'
        row['cell_temperature_screening']='ANNOTATED' if row['cell_temperature_quality'] else 'NO_FLAG'
    frame=pd.DataFrame(records)
    frame.attrs['use_time']=use_time
    frame.attrs['x_domain']=[min(recording.observations[i].timestamp_s if use_time else recording.observations[i].row_number for i in indices),
                             max(recording.observations[i].timestamp_s if use_time else recording.observations[i].row_number for i in indices)]
    if frame.attrs['x_domain'][0]==frame.attrs['x_domain'][1]:
        frame.attrs['x_domain']=[frame.attrs['x_domain'][0]-.5,frame.attrs['x_domain'][1]+.5]
    return frame


def _series(frame,key,label,quality_column=None):
    if frame.empty or not frame[key].notna().any():
        st.caption(f'{label}: unavailable with current signal/time definitions.')
        return
    use_time=frame.attrs.get('use_time',False)
    base=alt.Chart(frame).encode(x=alt.X('x:Q',scale=alt.Scale(domain=frame.attrs['x_domain']),title='Recording seconds (see source time interpretation)' if use_time else 'Worksheet row — NOT time'),
        y=alt.Y(key+':Q',title=label),tooltip=['row_number','timestamp_s',key,'candidate_label'])
    points=base.mark_point(size=18).encode(color=(quality_column or 'candidate_label')+':N')
    chart=(base.mark_line().encode(detail=('group_'+key)+':N',order='row_number:Q')+points) if use_time else points
    st.altair_chart(chart,width='stretch')


def render_dynamics(recording,analysis,frame):
    st.subheader('Smoothed acceleration and operating candidates')
    st.caption('Causal trailing-median smoothing and thresholds are configurable above. Dynamic states are inferred; source-reported charging codes remain separate. No derivative crosses a boundary, unusable endpoint or configured long interval.')
    _series(frame,'acceleration_m_s2','Acceleration (m/s²)')
    counts=Counter(state for i in st.session_state['_ev_plot_indices'] for state in analysis.operating[i].candidates)
    st.dataframe(pd.DataFrame([{'candidate':key,'observations':value} for key,value in counts.items()]))
    if not frame.empty:
        st.dataframe(frame[['row_number','timestamp_s','smoothed_speed_kmh','acceleration_m_s2','candidate_label','source_reported_state','state_verification','state_warnings']].head(200))
    st.json(analysis.configuration['operating'],expanded=False)


def render_electrical(recording,analysis,frame):
    st.subheader('Signed energy over accepted intervals')
    energy=analysis.energy
    for column,key in zip(st.columns(4),('signed_net_kwh','positive_signed_kwh','negative_signed_kwh','absolute_throughput_kwh')):
        column.metric(key,f'{energy[key]:.5g} kWh')
    st.caption(f"Whole-recording coverage: {energy['included_intervals']} included intervals, {energy['excluded_intervals']} excluded; {energy['included_duration_s']:g} included seconds. Selected telemetry plots do not change whole-recording totals; per-session totals are in Session Explorer.")
    st.warning('Signed components retain measured polarity. They are not verified charging/discharging energy or vehicle efficiency. Inferred timestamps and input-quality warnings propagate into this estimate.')
    st.json(energy,expanded=False)
    histogram=pd.DataFrame(analysis.electrical['power_distribution'])
    if not histogram.empty:
        st.subheader('Whole-recording power distribution (quality-annotated numeric values)')
        st.altair_chart(alt.Chart(histogram).mark_bar().encode(x=alt.X('lower_kw:Q',title='Signed kW'),x2='upper_kw:Q',y=alt.Y('count:Q',title='Observations'),tooltip=list(histogram.columns)),width='stretch')
    if frame.empty:return
    for x,y,title in [('battery_current_measured_a','battery_voltage_v','Voltage versus measured current'),('speed_kmh','battery_voltage_v','Voltage versus vehicle speed'),('acceleration_m_s2','battery_voltage_v','Voltage during acceleration/deceleration candidates')]:
        pairs=frame.dropna(subset=[x,y])
        if pairs.empty:continue
        st.subheader(title)
        st.altair_chart(alt.Chart(pairs).mark_point(size=20).encode(x=alt.X(x+':Q'),y=alt.Y(y+':Q'),color='candidate_label:N',tooltip=['row_number','timestamp_s',x,y,'candidate_label']),width='stretch')
    st.caption('Same-row measurements in the selected interval, sampled for display. Correlation or a descriptive voltage response does not establish causation, internal resistance or battery degradation.')
    st.json(analysis.electrical,expanded=False)


def render_health(recording,analysis,frame):
    st.subheader('Cell-extrema and temperature-trend indicators')
    st.warning('These are measurement diagnostics, not confirmed battery defects, SOH, capacity or remaining-life estimates. Invalid sensor inputs can create artificial spreads; inspect propagated quality flags.')
    for key,label in [('cell_voltage_spread_v','Cell voltage max − min (V)'),('cell_temperature_spread_c','Cell temperature max − min (degC)'),('max_temperature_rate_c_s','Maximum-cell temperature trend (degC/s)'),('min_temperature_rate_c_s','Minimum-cell temperature trend (degC/s)')]:
        _series(frame,key,label,'cell_voltage_screening' if 'voltage' in key else 'cell_temperature_screening')
    if not frame.empty:
        st.dataframe(frame[['row_number','timestamp_s','cell_voltage_spread_v','cell_temperature_spread_c','cell_voltage_quality','cell_temperature_quality']].head(200))
    st.json(analysis.configuration['cells'],expanded=False)


def _select_session():
    st.session_state['ev_segment']=st.session_state['engineering_session']


def render_sessions(recording,analysis):
    st.subheader('Possible driving / charging recording segments')
    st.session_state['engineering_session']=st.session_state.get('ev_segment',-1)
    selected=st.selectbox('Inspect session (synchronizes all telemetry charts)',[-1]+list(range(len(analysis.sessions))),
        format_func=lambda value:'All possible sessions' if value==-1 else f'Possible session {value+1}',key='engineering_session',on_change=_select_session)
    st.caption('Segments use the existing possible-boundary evidence, not confirmed trip IDs. Source charging codes identify reported-mode intervals, not current polarity. SOC source-unit changes remain explicitly unverified when percent is unknown.')
    table=[]
    for s in analysis.sessions:
        table.append({'session':s['session_id'],'start_s':s['start_timestamp_s'],'end_s':s['end_timestamp_s'],'duration_s':s['duration_s'],
            'observations':s['observations'],'max_speed_kmh':s['speed_kmh']['max'],'voltage_min_v':s['battery_voltage_v']['min'],'voltage_max_v':s['battery_voltage_v']['max'],
            'current_min_a':s['battery_current_measured_a']['min'],'current_max_a':s['battery_current_measured_a']['max'],
            'soc_change_pct':s['soc_change_pct'],'raw_soc_change_source_units':s['soc_change_source_units'],'distance_km':s['distance_km'],
            'signed_net_kwh':s['energy']['signed_net_kwh'],'excluded_energy_intervals':s['energy']['excluded_intervals'],'flagged_rows':s['flagged_observations']})
    st.dataframe(pd.DataFrame(table))
    if selected>=0:
        st.json(analysis.sessions[selected])


def render_reports(recording,analysis):
    st.subheader('Engineering report and uncertainties')
    for warning in analysis.uncertainties:st.caption('• '+warning)
    if st.button('Prepare engineering reports',key='prepare_engineering_reports'):
        for suffix,exporter,mime in [('json',export_engineering_json,'application/json'),('md',export_engineering_markdown,'text/markdown'),('csv',export_engineering_csv,'text/csv')]:
            with tempfile.TemporaryFile(mode='w+',encoding='utf-8',newline='') as output:
                exporter(recording,analysis,output);output.seek(0)
                st.download_button('Download engineering '+suffix.upper(),output,file_name='engineering-report.'+suffix,mime=mime)
    st.caption('JSON/Markdown summarize provenance, measurements, derived quantities, inferred candidates, session statistics and limitations. CSV contains annotated per-observation features. Original recording JSON/CSV remain available under Exports & Source.')
