"""Small native Streamlit fragments plus an isolated SVG topology component."""
import time
import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components
from .can_physics import classical_frame,arbitrate,differential,PURPOSES
from .studio_diagrams import frame_html,topology_html,arbitration_html
from .studio_playback import Playhead,vehicle_experiment,inspect_event

ID_HELP='The 11-bit message ID determines identity and standard-data-frame priority (lower numerical ID wins). It comes from a network design, DBC/communication specification, recorded CAN trace, or manual simulated input. It is neither a universal signal definition nor a destination address.'


def pause_players():
    for value in st.session_state.values():
        if isinstance(value,Playhead):value.playing=False


def player(key,length,render):
    head=st.session_state.get(key)
    if head is None or head.length!=length:
        head=Playhead(length);st.session_state[key]=head
    timing,motion=st.columns([3,2])
    speed=timing.select_slider('Playback events / bits per second',options=[0.5,1.0,2.0,4.0],value=2.0,key=key+'_speed')
    reduced=motion.checkbox('Reduced motion / manual stepping',key=key+'_reduced')
    if reduced:head.playing=False
    @st.fragment(run_every=1/speed if head.playing else None)
    def play_fragment():
        now=time.monotonic();last=st.session_state.get(key+'_last',now)
        if head.playing and now-last>=1/speed:
            head.tick();st.session_state[key+'_last']=now
            if not head.playing:st.rerun()
        columns=st.columns(5)
        if columns[0].button('Start',key=key+'_start',disabled=reduced or head.index==length-1):
            head.playing=True;st.session_state[key+'_last']=now;st.rerun()
        if columns[1].button('Pause',key=key+'_pause'):
            head.playing=False;st.rerun()
        if columns[2].button('Previous',key=key+'_previous'):head.move(-1);st.rerun()
        if columns[3].button('Step',key=key+'_step'):head.move(1);st.rerun()
        if columns[4].button('Reset',key=key+'_reset'):head.reset();st.rerun()
        st.caption(f'Position {head.index+1} / {length} · '+('Playing' if head.playing else 'Paused'))
        render(head.index,head.playing,reduced)
    play_fragment()


def frame_diagram(identifier,payload):
    """Independent of DBC DLC: valid 0–8-byte frames still visualize without decoding."""
    st.session_state.pop('_studio_frame',None)
    st.session_state.setdefault('frame_field','Identifier')
    try:
        value=int(identifier,16);data=bytes.fromhex(payload)
        if len(data)>8:raise ValueError('Use at most eight bytes')
    except ValueError as error:st.error('Frame construction: '+str(error));return None
    ack=st.checkbox('Simulated receiver acknowledges',value=True,key='frame_ack',help='ⓘ Receiver ACK confirms correct link-layer reception, not application processing. No hardware ACK is measured.')
    try:frame=classical_frame(value,data)
    except ValueError as error:st.error(str(error));return None
    if not ack:frame=classical_frame(value,data,acknowledged=False)
    st.session_state['_studio_frame']=frame
    st.markdown(frame_html(frame,st.session_state.get('frame_field','Identifier')),unsafe_allow_html=True)
    columns=st.columns([2,1,2])
    field=columns[0].selectbox('Inspect frame field ⓘ',list(PURPOSES),key='frame_field',help='Select a field; hover each diagram tile for its purpose. The separate intermission follows EOF.')
    columns[1].metric('DLC ⓘ',frame['dlc'],help='This supported classical format uses DLC 0–8 equal to payload bytes. Edit payload length to change DLC; FD and other variants are unsupported.')
    selected=next(item for item in frame['fields'] if item['name']==field)
    columns[2].caption(PURPOSES[field]+f" Current: {''.join(map(str,selected['bits'])) or 'empty'} ({selected['length']} bits).")
    if st.checkbox('Advanced: CRC and transmitted stuffed bits',key='frame_advanced'):
        st.code(f"CRC-15/CAN = 0x{frame['crc']:04X} · {frame['stuff_count']} inserted stuff bits")
        st.caption('CRC input: unstuffed SOF through Data; polynomial 0x4599, initial/final XOR 0, MSB first. Stuffing covers SOF through the CRC sequence, NOT delimiters, ACK, EOF or intermission.')
        st.code('CRC input: '+''.join(map(str,frame['crc_input'])))
        st.markdown('<div class="wire-bits">'+''.join(f'<span class="{"stuff" if item["stuffed"] else "original"}" title="{"Inserted stuff bit" if item["stuffed"] else "Original bit "+str(item["source_index"])}">{item["bit"]}</span>' for item in frame['stuffed_region'])+'</div>',unsafe_allow_html=True)
        st.caption('Underlined orange bits are inserted complements after five identical bits. The receiver removes them before checking CRC. ACK is a simulated receiving peer; the transmitter sends recessive in that slot. Missing ACK error handling and retries are not simulated.')
    return frame


def arbitration_lab():
    st.subheader('Bitwise arbitration · standard 11-bit data frames')
    st.caption('Dominant 0 / recessive 1 wired-AND at each identifier bit. This is genuine identifier arbitration, not a bus-occupancy or latency model.')
    values=[]
    for index,column in enumerate(st.columns(3)):
        values.append(column.text_input(['Motor controller','BMS','Instrument cluster'][index]+' ID ⓘ',['0x120','0x124','0x3E0'][index],key=f'arb_id_{index}',help=ID_HELP))
    try:result=arbitrate([int(value,16) for value in values])
    except ValueError as error:st.error(str(error));return
    st.session_state['_arbitration']=result
    def render(index,playing,reduced):
        step=result['steps'][index]
        st.markdown(arbitration_html(result,index),unsafe_allow_html=True)
        st.metric('Bus bit · identifier position '+str(step['identifier_bit']),step['bus'])
        rows=[]
        for node,value in enumerate(result['identifiers']):
            status='LOST here: recessive 1 observed dominant 0' if node in step['lost'] else 'CONTENDING / dominant-compatible' if node in step['active'] else 'Previously lost — no longer drives bus'
            rows.append({'ECU':['Motor controller','BMS','Instrument cluster'][node],'ID':f'0x{value:03X}',
                'identifier_bits':''.join(map(str,result['bits'][node])),'TX this bit':step['sent'].get(node,'—'),'status':status})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.markdown('<div class="arbitration-bits">'+''.join(f'<span class="{"current" if column==index else ""}">{column}: {result["steps"][column]["bus"]}</span>' for column in range(11))+'</div>',unsafe_allow_html=True)
        if len(step['active'])==1:st.success(f"Identifier winner: 0x{result['winner']:03X}. Losing arbitration is normal, not a CAN error.")
    player('arbitration_play',11,render)


def differential_lab():
    st.subheader('Differential signalling · ideal high-speed CAN illustration')
    sequence=st.text_input('Logical bit sequence ⓘ','1100010110',key='diff_sequence',help='0 is dominant, 1 is recessive; 1–128 bits. These nominal voltages illustrate conventional high-speed CAN, not every CAN physical layer.')
    noise=st.checkbox('Add identical common-mode interference',key='diff_noise')
    amplitude=st.slider('Illustrative common-mode amplitude (V) ⓘ',0.0,1.0,0.5,0.1,key='diff_amplitude',help='The same deterministic disturbance is added to both lines. This is not a full EMC or transceiver common-mode-range model.')
    try:rows=differential(sequence,amplitude=amplitude if noise else 0)
    except ValueError as error:st.error(str(error));return
    st.session_state['_differential']=rows
    def render(index,playing,reduced):
        row=rows[index]
        st.write(f"Bit {index}: logical {row['bit']} · {row['state']} · CAN_H {row['CAN_H']:.2f} V · CAN_L {row['CAN_L']:.2f} V · Vdiff {row['Vdiff']:.2f} V")
        frame=pd.DataFrame(rows).melt(id_vars=['index'],value_vars=['CAN_H','CAN_L','CAN_H_original','CAN_L_original','Vdiff'],var_name='line',value_name='voltage')
        chart=alt.Chart(frame).mark_line(interpolate='step-after').encode(x=alt.X('index:Q',title='Logical bit index'),y=alt.Y('voltage:Q',title='Illustrative volts'),
            color=alt.Color('line:N',scale=alt.Scale(domain=['CAN_H','CAN_L','CAN_H_original','CAN_L_original','Vdiff'],range=['#8c6900','#2366be','#8c6900','#2366be','#147e8b'])),
            strokeDash=alt.StrokeDash('line:N'),tooltip=['index','line','voltage'])
        rule=alt.Chart(pd.DataFrame({'index':[index]})).mark_rule(color='#a9430b').encode(x='index:Q')
        st.altair_chart(chart+rule,width='stretch')
        st.caption('Nominal recessive ≈2.5/2.5 V, dominant ≈3.5/1.5 V. Equal disturbance cancels ideally in Vdiff. Real receivers have limited common-mode range, asymmetric coupling and imperfect rejection. No EMC/hardware validation is claimed.')
    player('differential_play',len(rows),render)


def vehicle_lab(experiment=None,key='vehicle_play'):
    if experiment is None:
        experiment=st.session_state.get('_vehicle_experiment')
        if experiment is None:
            experiment=vehicle_experiment();experiment['studio_vehicle']=True
            st.session_state['_vehicle_experiment']=experiment
    experiment={**experiment,'studio_vehicle':True}
    if not experiment['events']:st.info('No retained transmissions to animate.');return
    st.caption('Shared CAN_H/CAN_L segment · two 120 Ω end terminations ⓘ · Click an ECU or bus to inspect. Dashed local links are not CAN nodes; pulses denote actual retained events, not propagation speed.',help='Conventional high-speed CAN uses two end terminations to reduce reflections. This is not an electrical solver. Per-ECU reception is modeled broadcast observability backed by one python-can receiver.')
    def render(index,playing,reduced):
        event=inspect_event(experiment,index);st.session_state['_current_'+key]=event
        components.html(topology_html(experiment,event,playing=playing,reduced=reduced),height=650,scrolling=True)
        with st.expander('Current message and reception evidence',expanded=False):st.json(event)
    player(key,len(experiment['events']),render)
