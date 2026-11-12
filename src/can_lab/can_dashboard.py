"""Offline raw-CAN workspace. No automatic files, images or network downloads."""
from dataclasses import asdict
import io
import json
import math
from pathlib import Path
import pandas as pd
import streamlit as st
from .can_recording import CANConfig, investigate_candump
from .can_reports import export_can_json, export_can_markdown
from .engineering import analyze_engineering


def render_raw_can():
    st.subheader('Raw CAN investigation — v0.4 foundation')
    st.warning('Implemented and validated with synthetic fixtures only. A compatible real recording/DBC with independent physical references has not been selected. Successful decoding does not establish vehicle accuracy.')
    example=st.checkbox('Use repository synthetic CAN example',value=False,key='can_example')
    log=st.file_uploader('Classical candump recording',type=['log','txt'],key='can_log')
    dbc=st.file_uploader('Matching DBC (standard-ID classical integer signals only)',type=['dbc'],key='can_dbc')
    mapping=st.text_area('Explicit signal-to-Recording mapping JSON',value='[]',key='can_mapping')
    references=st.file_uploader('Optional independent reference JSON',type=['json'],key='can_references')
    with st.expander('Bounded investigation settings'):
        maximum=st.number_input('Maximum scanned non-comment records',min_value=1,max_value=20000,value=10000,step=100)
        basis=st.selectbox('Declared raw timestamp basis',['relative','unix'],key='can_time_basis')
        channel=st.text_input('Select channel (blank requires a single selected channel)',value='')
        start=st.text_input('Start seconds (blank = no lower bound)',value='')
        end=st.text_input('End seconds (blank = no upper bound)',value='')
    if st.button('Investigate raw CAN',key='can_investigate'):
        try:
            options=CANConfig(max_frames=int(maximum),max_preview_frames=min(100,int(maximum)),time_basis=basis,
                              channel=channel or None,start_s=float(start) if start.strip() else None,end_s=float(end) if end.strip() else None)
            source_meta=None;dbc_meta=None
            if example:
                root=Path.cwd()/'tests/fixtures/raw_can'
                if not root.exists():raise ValueError('Run from the repository root for the synthetic example, or supply uploads.')
                log=root/'example.log';dbc=root/'example.dbc'
                selected_mapping=json.loads((root/'mapping.json').read_text())
                reference=json.loads((root/'references.json').read_text())
                source_meta={'dataset_id':'VCAN-authored synthetic CAN fixture','kind':'synthetic_fixture','license':'MIT; scoped fixture LICENSE'}
            else:
                if log is None or dbc is None:raise ValueError('Provide both a recording and its independently justified matching DBC')
                selected_mapping=json.loads(mapping)
                reference=json.loads(references.getvalue()) if references else None
            st.session_state['_can_investigation']=investigate_candump(log,dbc,mapping=selected_mapping,config=options,
                references=reference,source_metadata=source_meta,dbc_metadata=dbc_meta)
            st.session_state.pop('_can_engineering',None)
        except (ValueError,OSError,UnicodeError) as error:
            st.error(str(error));return
    result=st.session_state.get('_can_investigation')
    if result is None:
        st.info('No source is required at startup. Select the tiny synthetic example or supply reviewed external inputs. Inputs are never copied or exported automatically.')
        return
    columns=st.columns(4)
    for column,key in zip(columns,('scanned_records','decoded_frames','unknown_id_frames','malformed_records')):
        column.metric(key,result.coverage[key])
    if result.coverage['limit_reached']:st.warning('Processing limit reached: coverage describes only the bounded scan, not the complete source.')
    st.json({'source':result.source,'dbc':result.dbc,'coverage':result.coverage,'configuration':result.configuration})
    st.subheader('DBC signal inspection')
    names=sorted({(entry.frame.arbitration_id,name) for entry in result.frames if entry.status=='decoded' for name in entry.signals})
    if names:
        identifier,name=st.selectbox('Decoded signal',names,format_func=lambda value:f'0x{value[0]:03X} / {value[1]}')
        entries=[entry for entry in result.frames if entry.status=='decoded' and entry.frame.arbitration_id==identifier and name in entry.signals]
        step=max(1,math.ceil(len(entries)/2000))
        frame=pd.DataFrame([{'timestamp_s':entry.frame.timestamp_s,'value':entry.signals[name]} for entry in entries[::step]])
        definition=result.definitions[str(identifier)]['signals'][name]
        st.caption(f"Unit: {definition['unit']} (DBC-declared); timestamp basis: {result.configuration['time_basis']} (user declaration). Points assert no continuity or cross-frame alignment.")
        st.scatter_chart(frame,x='timestamp_s',y='value')
        st.json(definition)
    st.subheader('Frame / signal provenance')
    if result.frames:
        ref=st.number_input('Frame-table reference',min_value=0,max_value=len(result.frames)-1,value=0)
        entry=result.frames[int(ref)]
        st.json(asdict(entry))
        st.caption('Frame payload is stored once in the global recording frame table. Each normalized observation references that table; unmapped signals remain in its decoded frame values.')
    st.subheader('Reference evidence and quality')
    st.json(result.validation)
    st.caption('Golden-vector interpretation checks, signal plausibility and independent physical measurement accuracy are different evidence levels. Raw inputs are preserved.')
    st.dataframe(pd.DataFrame([{'row':row.row_number,'frame_ref':row.raw['frame_ref'],'quality':json.dumps(row.quality)} for row in result.recording.observations[:100]]))
    if result.recording.observations and st.button('Analyze mapped observations with existing engineering tools',key='can_engineering'):
        st.session_state['_can_engineering']=analyze_engineering(result.recording)
    if st.session_state.get('_can_engineering') is not None:
        st.caption('Sparse per-frame data; no invented battery values or cross-frame simultaneity. Missing electrical inputs produce no accepted battery-energy intervals.')
        analysis=st.session_state['_can_engineering']
        st.json({'energy':analysis.energy,'limitations':analysis.uncertainties})
    if st.button('Prepare compact CAN reports',key='can_reports'):
        for extension,exporter,mime in [('json',export_can_json,'application/json'),('md',export_can_markdown,'text/markdown')]:
            buffer=io.StringIO();exporter(result,buffer)
            st.download_button('Download CAN '+extension.upper(),buffer.getvalue(),file_name='can-investigation.'+extension,mime=mime)
    st.caption('Reports are generated only on request. No plot images, raw-source copies, intermediate arrays or ZIP backups are saved automatically.')
