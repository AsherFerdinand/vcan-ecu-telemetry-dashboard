"""Small local visual system, with no remote assets or animation."""
STYLE='''<style>
:root {--vcan-orange:#a9430b;--vcan-navy:#152334;--vcan-ink:#162638;}
[data-testid="stAppViewContainer"] {background:#f5f6f8;color:var(--vcan-ink);}
[data-testid="stSidebar"] {background:var(--vcan-navy);}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p {color:#edf2f7;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#172638;}
[data-testid="stSidebar"] [data-baseweb="radio"] {accent-color:#f58a42;}
.block-container {max-width:1350px;padding-top:2rem;padding-bottom:2rem;}
[data-testid="stCaptionContainer"] p {color:#4b5a6b;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#c4cfdb;}
h1 {font-size:1.85rem !important;letter-spacing:-.03em;}
h2 {font-size:1.35rem !important;} h3 {font-size:1.08rem !important;}
[data-testid="stMetricValue"] {font-family:ui-monospace,Consolas,monospace;font-size:1.6rem;}
[data-testid="stVerticalBlockBorderWrapper"] {background:white;border-radius:10px;}
.vcan-kicker {font:600 .76rem ui-monospace,Consolas,monospace;letter-spacing:.09em;color:#a9430b;margin-bottom:.6rem;}
.vcan-bits {display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:1rem 0;}
.vcan-byte {background:#fff;border:1px solid #cbd3dd;border-radius:7px;padding:10px;font-family:ui-monospace,Consolas,monospace;}
.vcan-byte small {color:#425369;} .vcan-byte strong {display:block;font-size:1.3rem;margin:6px 0;}
.vcan-bit {display:inline-block;min-width:1.05em;text-align:center;color:#465466;}
.vcan-bit.used {background:#fff0e4;color:#8a3505;border-bottom:3px solid #a9430b;font-weight:700;}
.vcan-note {background:#eaf4ee;color:#175f3b;padding:.6rem .9rem;border-left:3px solid #23784a;}
button:focus-visible,input:focus-visible {outline:3px solid #a9430b !important;outline-offset:2px;}
@media(max-width:700px){.vcan-bits{grid-template-columns:repeat(2,minmax(115px,1fr));}.block-container{padding-top:1rem;}}
</style>'''
