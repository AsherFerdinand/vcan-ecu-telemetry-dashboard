"""Run with: python -m streamlit run src/can_lab/dashboard.py"""
import streamlit as st
from can_lab import __version__
from can_lab.workbench_style import STYLE
from can_lab.workbench_dashboard import PAGES,overview,frame_lab,network_lab,fault_lab,learn_can

st.set_page_config(page_title='VCAN · Engineering Workbench',layout='wide')
st.markdown(STYLE,unsafe_allow_html=True)
with st.sidebar:
    st.markdown('## VCAN')
    st.caption('AUTOMOTIVE ENGINEERING WORKBENCH')
    st.radio('Workspace',PAGES,key='workbench_page')
    with st.expander('Existing data workflows',expanded=False):
        def select_source():
            st.session_state['workbench_page']='Vehicle data'
        source=st.selectbox('Data Source',['Virtual ECU Simulation','Imported CAN Log','Real-World EV Dataset','Raw CAN Investigation (v0.4 foundation)'],key='data_source',on_change=select_source)
    st.caption('CLASSICAL CAN · DBC · TELEMETRY')
    st.caption('Simulated teaching / source-qualified data')
st.title('Automotive CAN & Telemetry Laboratory')
st.caption(f'VCAN {__version__} · Configure → Run → Observe → Investigate → Explain')
page=st.session_state['workbench_page']
if page=='Overview':overview()
elif page=='Frame Laboratory':frame_lab()
elif page=='Virtual CAN Network':network_lab()
elif page=='Fault Investigation':fault_lab()
elif page=='Learn CAN':learn_can()
else:
    st.caption('Current data workflow: '+source+' · Change it in the sidebar’s Existing data workflows menu.')
    from can_lab.telemetry_dashboard import render_data_workspace
    render_data_workspace(source)
