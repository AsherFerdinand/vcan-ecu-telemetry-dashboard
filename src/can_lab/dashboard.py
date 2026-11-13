"""Run with: python -m streamlit run src/can_lab/dashboard.py"""
import streamlit as st
from can_lab import __version__
from can_lab.workbench_style import STYLE
from can_lab.workbench_dashboard import PAGES,overview,frame_lab,network_lab,fault_lab,learn_can

st.set_page_config(page_title='VCAN · Engineering Workbench',layout='wide')
st.markdown(STYLE,unsafe_allow_html=True)
st.markdown('<div class="studio-brand">VCAN <span>VISUAL CAN ENGINEERING STUDIO</span></div>',unsafe_allow_html=True)
from can_lab.studio_dashboard import pause_players as stop_playback

st.segmented_control('Workspace',PAGES,key='workbench_page',default='Overview',required=True,on_change=stop_playback,
    format_func=lambda page:{'Frame Laboratory':'CAN Frame Lab','Virtual CAN Network':'Vehicle Network','Vehicle data':'Vehicle Data'}.get(page,page),width='stretch')
with st.expander('Existing data workflows',expanded=False):
    def select_source():
        stop_playback()
        st.session_state['workbench_page']='Vehicle data'
    source=st.selectbox('Data Source',['Virtual ECU Simulation','Imported CAN Log','Real-World EV Dataset','Raw CAN Investigation (v0.4 foundation)'],key='data_source',on_change=select_source)
st.title('Automotive CAN & Telemetry Laboratory')
st.caption(f'VCAN {__version__} · Configure → Run → Observe → Investigate → Explain')
page=st.session_state['workbench_page']
if page=='Overview':overview()
elif page=='Frame Laboratory':frame_lab()
elif page=='Virtual CAN Network':network_lab()
elif page=='Fault Investigation':fault_lab()
elif page=='Learn CAN':learn_can()
else:
    st.caption('Current data workflow: '+source+' · Change it in the Existing data workflows menu above.')
    from can_lab.telemetry_dashboard import render_data_workspace
    render_data_workspace(source)
