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

STYLE=STYLE.replace('</style>','''
.studio-brand{background:#152334;color:#f3f7fa;padding:12px 18px;border-radius:8px;font:700 1.15rem ui-monospace,Consolas,monospace;}
.studio-brand span{font-size:.78rem;color:#b6edf5;margin-left:1rem;letter-spacing:.08em;}
.frame-grid{display:flex;flex-wrap:wrap;gap:5px;padding:12px 0}.frame-cell{flex:1 1 65px;min-width:0;border-radius:6px;padding:7px;color:#162638;}
.frame-cell:nth-child(7){flex:4 1 180px}.frame-cell:nth-child(8){flex:2 1 100px}
.frame-cell small{display:block;font-size:.65rem}.frame-cell b{font-size:.75rem}.frame-cell code{display:block;word-break:break-all;font-size:.68rem}
.frame-cell:has(code){overflow-wrap:anywhere}.wire-bits{display:flex;flex-wrap:wrap;gap:4px;font:14px ui-monospace,monospace}.wire-bits span{padding:2px 4px}.wire-bits .stuff{background:#ffe1bf;border-bottom:2px solid #9a3b00}
.arb-table{width:100%;border-collapse:collapse;font:12px ui-monospace,monospace}.arb-table caption{color:#425369;text-align:left;padding:8px}.arb-table th,.arb-table td{border:1px solid #b6c7d5;text-align:center;padding:6px}.arb-table .compared{outline:3px solid #a9430b;outline-offset:-3px;background:#fff1de}.arb-table .lost{color:#a12727;background:#fff0f0}
.arbitration-bits{display:flex;flex-wrap:wrap;gap:8px}.arbitration-bits span{padding:5px;border:1px solid #a8bac8;font-family:monospace}.arbitration-bits .current{border:3px solid #a9430b;background:#fff0de}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media(max-width:1100px){.block-container{padding-left:1rem;padding-right:1rem}h1{font-size:1.45rem!important}}
</style>''')
