"""Configure → Run → Observe → Investigate → Explain, within the existing app."""
import re
import math
import pandas as pd
import altair as alt
import streamlit as st
from .workbench import (EXAMPLE_ID,EXAMPLE_PAYLOAD,Node,teaching_database,
                        decode_teaching_frame,network,fault_findings)
from .learning import FAQ,QUESTIONS,score_quiz

PAGES=['Overview','Frame Laboratory','Virtual CAN Network','Fault Investigation','Vehicle data','Learn CAN']


def open_page(page,source=None):
    st.session_state['workbench_page']=page
    if source:st.session_state['data_source']=source


def learn_button(topic,key):
    def jump():
        st.session_state['learn_topic']=topic
        open_page('Learn CAN')
    st.button('Learn: '+topic,key=key,on_click=jump)


def overview():
    st.markdown('<div class="vcan-kicker">WORKSPACE / AUTOMOTIVE ENGINEERING</div>',unsafe_allow_html=True)
    st.header('Explore the measurement. Follow the evidence.')
    st.write('Configure an experiment, run it, inspect the actual results, then investigate how they were produced.')
    cards=[('Frame Laboratory','CLASSICAL CAN · DBC','Synthetic-validated / offline teaching','Inspect payload bits, raw integers and physical scaling.','Frame Laboratory',None),
           ('Virtual CAN Network','PYTHON-CAN · VIRTUAL','Simulated','Configure four educational nodes and inspect logical message arrivals.','Virtual CAN Network',None),
           ('Fault Investigation','SYNTHETIC · CONTROLLED RULES','Simulated / known injections','Compare timing, missing-message and signal-rate evidence against thresholds.','Fault Investigation',None),
           ('Raw CAN Investigation','CLASSICAL CAN · CANDUMP','Real-data demonstrated / Level 2','Trace source-reported vehicle frames to DBC signals; physical validation pending.','Vehicle data','Raw CAN Investigation (v0.4 foundation)'),
           ('EV Telemetry & Diagnostics','DECODED WORKBOOK · RECORDING','Implemented / source-qualified','Review quality, replay, operating states, cell indicators and requested reports.','Vehicle data','Real-World EV Dataset'),
           ('Learning Laboratory','CAN · ENGINEERING REASONING','Implemented / local','Explore a practical FAQ and test your understanding with explained answers.','Learn CAN',None)]
    for start in (0,3):
        for column,card in zip(st.columns(3),cards[start:start+3]):
            name,protocol,status,description,page,source=card
            with column:
                with st.container(border=True):
                    st.caption(protocol)
                    st.subheader(name)
                    st.write(description)
                    st.caption(status)
                    st.button('Open '+name,key='open_'+page+str(source),on_click=open_page,args=(page,source),width='stretch')
    st.info('Real vehicle CAN decoding demonstrated at DBC interpretation Level 2; independent physical validation pending. The KUKSA capture/date attribution and licensing caveats remain documented.')
    st.caption('Raw frames → explicit DBC → sparse Recording → quality and engineering → requested reports. Already-decoded EV telemetry enters at Recording. Teaching experiments are not real vehicle topology or a production anomaly detector.')


def reset_frame():
    st.session_state['frame_id']=EXAMPLE_ID
    st.session_state['frame_payload']=EXAMPLE_PAYLOAD
    st.session_state['frame_signal']='DI_vehicleSpeed'
    st.session_state.pop('_frame_result',None)


def frame_lab():
    st.markdown('<div class="vcan-kicker">CAN LABORATORY / PAYLOAD TO MEASUREMENT</div>',unsafe_allow_html=True)
    st.header('CAN Frame Laboratory')
    st.caption('Offline teaching definitions. KUKSA speed is derived from the documented DBC; other examples use authored synthetic definitions. No external dataset is needed.')
    st.session_state.setdefault('frame_id',EXAMPLE_ID)
    st.session_state.setdefault('frame_payload',EXAMPLE_PAYLOAD)
    left,right=st.columns([2,3])
    with left:
        st.subheader('01 / Configure')
        identifier=st.text_input('Arbitration ID (hex)',key='frame_id')
        payload=st.text_input('Payload bytes (hex)',key='frame_payload')
        try:
            db=teaching_database();message=db.get_message_by_frame_id(int(identifier,16))
            options=[signal.name for signal in message.signals]
        except (ValueError,KeyError):options=['DI_vehicleSpeed']
        if st.session_state.get('frame_signal') not in options:st.session_state['frame_signal']=options[0]
        selected=st.selectbox('DBC signal',options,key='frame_signal')
        st.caption('Examples: 0x257 speed; 0x100 original RPM/speed; 0x200 temperature; 0x300 signed Motorola teaching signal.')
        st.button('Reset verified example',key='frame_reset',on_click=reset_frame)
    # Recompute on every valid input change. Button makes the workflow explicit;
    # nothing is retained from an older payload after an invalid edit.
    with right:
        st.subheader('02 / Run & observe')
        st.button('Decode frame',key='frame_decode')
        try:result=decode_teaching_frame(identifier,payload,selected)
        except ValueError as error:
            st.session_state.pop('_frame_result',None);st.error(str(error));return
        st.session_state['_frame_result']=result
        a,b=st.columns(2)
        a.metric('Raw integer',result['raw_integer'])
        b.metric(f"Physical ({result['unit']})",f"{result['physical']:.6g}")
        st.caption(f"Scale: {result['scale']} · Offset: {result['offset']}")
        st.code(f"{result['raw_integer']} × {result['scale']} + ({result['offset']}) = {result['physical']:.6g} {result['unit']}")
        if result['frame_id']==0x257 and result['signal']=='DI_vehicleSpeed' and result['payload_hex']==EXAMPLE_PAYLOAD and math.isclose(result['physical'],3.04,abs_tol=1e-10):
            st.success('Known byte vector matches the manual 3.04 km/h interpretation check.')
        st.caption('Changed payloads produce newly computed values; the verified 3.04 km/h result is not a fixed label.')
    st.subheader('03 / Investigate bytes and bits')
    bits=set(result['bits']);cells=[]
    for byte,value in enumerate(result['bytes']):
        binary=''.join(f'<span class="vcan-bit {"used" if byte*8+bit in bits else ""}" title="DBC bit {byte*8+bit}{" selected" if byte*8+bit in bits else ""}">{(value>>bit)&1}</span>' for bit in range(7,-1,-1))
        cells.append(f'<div class="vcan-byte"><small>BYTE {byte} · bits {byte*8+7}…{byte*8}</small><strong>{value:02X}</strong>{binary}</div>')
    st.markdown('<div class="vcan-bits">'+''.join(cells)+'</div>',unsafe_allow_html=True)
    st.caption('Underlined orange bits belong to the selected signal. Display within each byte is MSB → LSB; DBC bit numbers remain byte-local LSB=0. An accessible data table below records the selected bits.')
    st.dataframe(pd.DataFrame([{'byte_index':index,'hex':f'{value:02X}','binary':f'{value:08b}',
        'selected_DBC_bits':', '.join(str(bit) for bit in range(index*8,index*8+8) if bit in bits)} for index,value in enumerate(result['bytes'])]),hide_index=True,width='stretch')
    with st.expander('How did VCAN calculate this?'):
        st.json({key:result[key] for key in ('frame_id','signal','start_bit','length','byte_order','signed','raw_integer','unsigned_integer','scale','offset')})
        st.write('cantools performs both unscaled integer extraction and physical decoding using the existing VCAN codec loader. The bit display only traverses the signal definition; it is not a second decoder.')
        st.write('Intel starts at the least significant signal bit and advances through increasing DBC bit numbers. Motorola starts at the most significant signal bit: decrease within a byte, then jump from bit 0 to bit 15 of the next byte.')
        st.code('Selected DBC bits in signal traversal order: '+', '.join(map(str,result['bits'])))
        if result['signed']:st.write('Two’s complement: if the top signal bit is set, subtract 2^length from the unsigned integer. Scaling applies to the resulting signed integer.')
    with st.expander('Does successful decoding prove the actual vehicle travelled at 3.04 km/h?'):
        st.write('No. This is interpretation according to a documented DBC (Level 2). Independent physical validation needs compatible acquisition metadata and synchronized calibrated or authoritative measurements with justified tolerances.')
    learn_button('Byte order','frame_learn')


def default_nodes():
    return [Node('Powertrain ECU',0x100,100),Node('Battery Management System',0x200,200),
            Node('Vehicle Control Unit',0x300,250),Node('Instrument Cluster',0x400,500)]


def render_network_result(result):
    st.subheader('03 / Observe & investigate')
    st.caption(result['assumptions'])
    st.code('Powertrain · BMS · VCU · Cluster → python-can virtual bus → shared observer',language=None)
    st.caption('Four educational publishers. Default 0x100/0x200 use the original synthetic signal definitions; other IDs carry uninterpreted teaching payloads.')
    for column,node in zip(st.columns(4),result['nodes']):
        column.metric(node['name'],result['counts'][node['name']],help=f"Standard ID 0x{node['frame_id']:03X}; period {node['period_ms']} ms; logical received count")
    data=pd.DataFrame(result['events'])
    if data.empty:st.info('No transmissions: all configured nodes are disabled or stopped before their first release.');return
    chart=alt.Chart(data).mark_tick(thickness=3,size=24).encode(
        x=alt.X('timestamp_ms:Q',title='Logical release time (ms)'),y=alt.Y('node:N',title=None),
        color=alt.Color('node:N',legend=None),tooltip=['node','timestamp_ms','frame_id','payload_hex','interval_ms'])
    st.altair_chart(chart,width='stretch')
    st.dataframe(data,hide_index=True,width='stretch')
    if not 0<=st.session_state.get('network_event',0)<len(result['events']):st.session_state['network_event']=0
    event=st.number_input('Inspect event index',0,len(result['events'])-1,0,key='network_event')
    st.json(result['events'][event])


def network_preset():
    scenario=st.session_state['network_scenario']
    for index,node in enumerate(default_nodes()):
        st.session_state[f'node_period_{index}']=([100,170,260,430][index] if scenario=='Different message periods' else 100 if scenario=='Simultaneous releases' else node.period_ms)
        st.session_state[f'node_phase_{index}']=0 if scenario=='Simultaneous releases' else index*10
    st.session_state.pop('_network_result',None)


def network_lab():
    st.markdown('<div class="vcan-kicker">CAN LABORATORY / VIRTUAL TRANSPORT</div>',unsafe_allow_html=True)
    st.header('Virtual CAN Network')
    st.write('Configure educational publishers and observe deterministic message arrivals at a shared receiving node. These are not actual KUKSA ECUs.')
    scenario=st.selectbox('Scenario',['Normal periodic communication','Simultaneous releases','One ECU stops','Different message periods'],key='network_scenario',on_change=network_preset)
    with st.form('network_configuration'):
        duration=st.number_input('Duration (ms)',100,10000,1500,100,key='network_duration')
        nodes=[]
        for index,column in enumerate(st.columns(4)):
            with column:
                node=default_nodes()[index]
                st.subheader(node.name)
                enabled=st.checkbox('Transmit',True,key=f'node_enabled_{index}')
                identifier=st.text_input('Standard ID (hex)',f'0x{node.frame_id:03X}',key=f'node_id_{index}')
                period=st.number_input('Period (ms)',10,2000,node.period_ms,10,key=f'node_period_{index}')
                phase=st.number_input('First release (ms)',0,2000,index*10,10,key=f'node_phase_{index}')
                payload=st.text_input('Optional payload override (hex bytes)',key=f'node_payload_{index}')
                nodes.append((node.name,identifier,period,enabled,re.sub(r'\s','',payload) if payload else None,phase))
        stop=st.number_input('Powertrain stop time (ms; stopping scenario only)',0,10000,500,100,key='network_stop')
        run=st.form_submit_button('Run network experiment',key='network_run')
    st.caption('Scenario presets change actual periods and first-release phases. You may then edit them before running. Simultaneous releases use a common phase; ID order is display order, not an arbitration timing simulation.')
    if run:
        try:
            selected=[Node(name,int(identifier,16),period,enabled,payload,stop if index==0 and scenario=='One ECU stops' else None,phase) for index,(name,identifier,period,enabled,payload,phase) in enumerate(nodes)]
            st.session_state['_network_result']=network(selected,duration_ms=duration)
        except ValueError as error:st.error(str(error));st.session_state.pop('_network_result',None)
    result=st.session_state.get('_network_result')
    if result:
        st.caption('Last completed run; edit controls and run again to replace these results.')
        render_network_result(result)
        with st.expander('Why do simultaneous releases share a timestamp?'):
            st.write('The software schedules releases without calculating frame occupancy. On a real bus, standard data-frame arbitration gives the lower ID priority and delays other transmitters. This timeline does not model that delay, bitrate, retransmission or same-ID collisions; duplicate IDs are rejected.')
    learn_button('Arbitration','network_learn')


def fault_lab():
    st.markdown('<div class="vcan-kicker">CAN LABORATORY / KNOWN SYNTHETIC INJECTIONS</div>',unsafe_allow_html=True)
    st.header('CAN Fault Investigation')
    st.warning('Educational rules with known synthetic ground truth, not a validated production anomaly detector. Original recordings are never modified.')
    with st.form('fault_configuration'):
        scenario=st.selectbox('Injected event',['Missing message','Timing irregularity','Signal discontinuity'],key='fault_scenario')
        a,b=st.columns(2)
        with a:
            period=st.number_input('Expected period (ms)',50,500,100,10,key='fault_period')
            stop=st.number_input('Stop / jump time (ms)',100,1400,500,100,key='fault_at')
            jitter=st.number_input('Alternating release delay (ms)',0,49,30,key='fault_jitter')
        with b:
            factor=st.number_input('Missing-message threshold (× period)',1.0,10.0,2.5,0.5,key='fault_missing_factor')
            tolerance=st.number_input('Timing deviation threshold (ms)',1,100,20,key='fault_tolerance')
            rate=st.number_input('Speed-rate threshold (km/h/s)',1,2000,100,10,key='fault_rate')
            jump=st.number_input('Synthetic speed step (km/h)',0,150,60,10,key='fault_jump')
        run=st.form_submit_button('Run controlled investigation',key='fault_run')
    if run:
        try:
            node=Node('Powertrain ECU',0x100,period,stop_ms=stop if scenario=='Missing message' else None)
            result=network([node],duration_ms=1500,jitter_node=node.name if scenario=='Timing irregularity' else None,
                jitter_ms=jitter if scenario=='Timing irregularity' else 0,jump_node=node.name if scenario=='Signal discontinuity' else None,
                jump_at_ms=stop,jump_kmh=jump)
            evidence=fault_findings(result,missing_factor=factor,timing_tolerance_ms=tolerance,rate_threshold_kmh_s=rate)
            st.session_state['_fault_result']=(result,evidence,scenario)
        except ValueError as error:st.error(str(error));st.session_state.pop('_fault_result',None)
    if '_fault_result' in st.session_state:
        result,evidence,scenario=st.session_state['_fault_result']
        st.subheader('Observe: configured ground truth')
        st.json({'scenario':scenario,'nodes':result['nodes'],'injection':result['ground_truth']})
        frame=pd.DataFrame(result['events'])
        st.altair_chart(alt.Chart(frame).mark_line(point=True).encode(x=alt.X('timestamp_ms:Q',title='Logical timestamp (ms)'),
            y=alt.Y('speed_kmh:Q',title='Original synthetic speed (km/h)'),tooltip=['index','timestamp_ms','speed_kmh']),width='stretch')
        kind={'Missing message':'missing_message','Timing irregularity':'timing','Signal discontinuity':'signal_rate'}[scenario]
        selected=[item for item in evidence if item['kind']==kind]
        st.metric('Selected-rule threshold exceedances',sum(item['exceeded'] for item in selected))
        if selected:
            st.dataframe(pd.DataFrame(selected),hide_index=True,width='stretch')
            if st.session_state.get('fault_evidence',0) not in range(len(selected)):st.session_state['fault_evidence']=0
            inspected=st.selectbox('Inspect diagnostic evidence',range(len(selected)),format_func=lambda index:f"Finding {index} · {'threshold exceeded' if selected[index]['exceeded'] else 'within threshold'}",key='fault_evidence')
            finding=selected[inspected];st.json(finding)
            st.json([result['events'][index] for index in finding['evidence_indices']])
        else:st.info('The selected rule did not produce evidence above the configured threshold within this observation horizon.')
        with st.expander('Explain this result'):
            st.write('Missing: observed silence > expected period × multiplier. Timing: |observed interval − expected period| > tolerance. Signal: |(current − previous) / elapsed seconds| > rate threshold. Equality does not exceed the threshold.')
            st.write('Every finding references the unchanged input events by index. The last-silence check also records the experiment end. A release schedule is known here because we generated it; a real capture requires independently justified expectations.')
            st.write('Recording gaps, changing rates, uncertain clocks, normal operating transitions and incomplete captures can produce similar evidence. A threshold crossing is not a confirmed ECU failure.')
    learn_button('Missing messages','fault_learn')


def reset_quiz():
    for key in list(st.session_state):
        if key.startswith('quiz_answer_') or key=='_quiz_result':del st.session_state[key]


def learn_can():
    st.markdown('<div class="vcan-kicker">LEARN CAN / LOCAL KNOWLEDGE LABORATORY</div>',unsafe_allow_html=True)
    st.header('Learn CAN')
    faq,quiz=st.tabs(['Fundamentals & FAQ','Knowledge Check'])
    with faq:
        if st.session_state.get('learn_topic'):st.info('Context from your experiment: '+st.session_state['learn_topic'])
        for index,(question,beginner,detail) in enumerate(FAQ,1):
            with st.expander(f'{index:02d} / {question}'):
                st.write(beginner)
                st.caption('Engineering detail')
                st.write(detail)
    with quiz:
        level=st.selectbox('Knowledge level',['Beginner','Intermediate'],key='quiz_level',on_change=reset_quiz)
        st.caption('Local and deterministic. No account, score upload or personal information.')
        questions=[question for question in QUESTIONS if question['level']==level]
        answers={}
        for question in questions:
            st.caption(question['category'])
            value=st.radio(question['question'],question['choices'],index=None,key='quiz_answer_'+question['id'])
            answers[question['id']]=question['choices'].index(value) if value is not None else None
            with st.expander('Hint · '+question['category']):st.write(question['hint'])
        st.button('Retry knowledge check',key='quiz_retry',on_click=reset_quiz)
        if st.button('Check answers',key='quiz_submit'):
            st.session_state['_quiz_result']={**score_quiz(level,answers),'submitted_answers':answers}
        result=st.session_state.get('_quiz_result')
        if result and result['submitted_answers']!=answers:
            st.session_state.pop('_quiz_result',None);result=None
        if result:
            st.metric('Score',f"{result['score']} / {result['total']}")
            for question,item in zip(questions,result['feedback']):
                st.write(('✓ Correct' if item['correct'] else '○ Unanswered' if not item['answered'] else '× Review')+' · '+question['category'])
                st.caption(item['explanation'])
