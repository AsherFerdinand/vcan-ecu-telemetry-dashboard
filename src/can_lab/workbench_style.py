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


def appearance_style(theme):
    """Native Streamlit handles widget/chart themes; match custom surfaces to it."""
    dark=theme=='dark'
    bg,surface,ink,muted,border=('#0b1220','#152237','#edf3fb','#b4c5d8','#445b76') if dark else ('#f5f7fa','#ffffff','#162638','#42566c','#b7c5d4')
    return STYLE+f'''<style>
    [data-testid="stAppViewContainer"]{{background:{bg};color:{ink}}}
    h1,h2,h3,[data-testid="stMarkdownContainer"],label{{color:inherit}}
    [data-testid="stCaptionContainer"] p,.vcan-byte small,.arb-table caption{{color:{muted}}}
    [data-testid="stVerticalBlockBorderWrapper"],.vcan-byte{{background:{surface};border-color:{border};color:{ink}}}
    [data-testid="stVerticalBlockBorderWrapper"]{{transition:border-color .12s ease}}
    [data-testid="stVerticalBlockBorderWrapper"]:hover{{border-color:#39cce4}}
    [data-testid="stVerticalBlockBorderWrapper"]:focus-within{{outline:2px solid #ff9b51;outline-offset:2px}}
    .vcan-bit{{color:{muted}}}.vcan-bit.used{{background:#403020;color:#ffcc91;border-color:#ff9b51}}
    .vcan-kicker{{color:{'#ffb67d' if dark else '#963c09'}}}
    .frame-cell{{color:#162638}} .arb-table td,.arb-table th{{border-color:{border}}}
    .arb-table .compared,.arbitration-bits .current{{color:#162638}} .arb-table .lost{{color:#9e2525}}
    [class*="st-key-module_card_"]{{background:{surface};border:1px solid {border};border-radius:10px;padding:14px}}
    [class*="st-key-module_card_"]:hover{{border-color:#39cce4}}
    [class*="st-key-module_card_"]:focus-within{{outline:2px solid #ff9b51}}
    .card-icon{{height:58px;display:flex;align-items:center;color:#39cce4}}.card-icon svg{{width:100px;height:50px}}
    .capability{{display:inline-block;padding:3px 7px;border:1px solid {border};border-radius:20px;color:{muted};font:11px ui-monospace,monospace}}
    </style>'''


def overview_icon(index):
    shapes=[
        '<rect x="4" y="8" width="90" height="32" rx="4"/><path d="M25 8v32m20-32v32m20-32v32"/><path d="M49 16h10v17H49Z" fill="#ff9b51"/>',
        '<rect x="30" y="3" width="40" height="44" rx="15"/><path d="M48 8v34M54 8v34M10 15h38m6 20h35"/><rect x="3" y="10" width="17" height="12"/><rect x="78" y="29" width="17" height="12"/>',
        '<path d="M3 32h22l8-20 8 25 10-9h12l8-21 7 26h19"/><circle cx="71" cy="13" r="10" stroke="#ff9b51"/>',
        '<rect x="3" y="7" width="50" height="35" rx="4"/><path d="M60 24h32m-8-8 8 8-8 8"/><text x="8" y="29" fill="currentColor" stroke="none" font-size="12">0x257</text>',
        '<rect x="5" y="10" width="42" height="30" rx="4"/><path d="M47 20h5v10h-5M12 17h8v16h-8m12-16h8v16h-8M60 38V12m0 26h35m-30-8 9-13 9 8 10-18"/>',
        '<path d="M8 10q20-8 40 0 20-8 40 0v32q-20-8-40 0-20-8-40 0Z M48 10v32 M17 19h21m-21 8h17m25-8h20m-20 8h15"/>']
    return '<div class="card-icon"><svg viewBox="0 0 100 50" role="img" aria-label="Module illustration" fill="none" stroke="currentColor" stroke-width="2">'+shapes[index]+'</svg></div>'
