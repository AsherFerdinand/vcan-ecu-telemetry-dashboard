"""Original SVG/HTML views of computed model data; no external assets."""
import html
import json

COLORS={'SOF':'#dbe6ef','Identifier':'#b5f0f7','Data':'#e4d4fa','CRC sequence':'#ffe3bd','ACK slot':'#c1ecd5','Intermission':'#e4e7eb'}


def frame_html(frame,selected):
    cells=[]
    for field in frame['fields']:
        name=field['name'];value=''.join(map(str,field['bits'])) or 'empty'
        outline='3px solid #a9430b' if name==selected else '1px solid #9baaba'
        cells.append(f'<div class="frame-cell" style="background:{COLORS.get(name,"#edf2f6")};border:{outline}" title="{html.escape(field["purpose"],quote=True)}"><b>{html.escape(name)}</b><small>{field["length"]} bit(s){" · AFTER FRAME" if not field["inside_frame"] else ""}</small><code>{value}</code></div>')
    return '<div class="frame-grid" aria-label="Standard classical data frame and following intermission">'+''.join(cells)+'</div>'


def topology_html(experiment,event,*,playing=False,reduced=False):
    """Isolated component contract: immutable experiment + inspected event → HTML.

    JS only selects a local information panel. Simulation and playback remain Python.
    Pulses denote the current actual event, not calculated signal propagation.
    """
    nodes=[node['name'] for node in experiment['nodes']]
    if experiment.get('studio_vehicle'):nodes+=['Brake ECU']
    active=event['node']
    positions=[(190,115),(190,285),(530,115),(530,285),(530,410)]
    svg=['<svg viewBox="0 0 720 500" role="img" aria-label="Educational vehicle, one shared terminated differential CAN bus">',
         '<rect x="100" y="20" width="520" height="440" rx="100" fill="#f1f4f7" stroke="#889aab" stroke-width="3"/>',
         '<path d="M130 70h-35v80h35M130 330H95v80h35M610 70h35v80h-35M610 330h35v80h-35" stroke="#182c40" stroke-width="16" fill="none"/>',
         '<rect x="235" y="180" width="95" height="60" rx="12" fill="#d8e7de" stroke="#337451"/><text x="282" y="205" text-anchor="middle" font-size="12">Battery pack</text>',
         '<circle cx="360" cy="60" r="24" fill="#d7e5ed" stroke="#426173"/><text x="360" y="64" text-anchor="middle">Motor</text>',
         '<path d="M336 60H300V105H273M282 240V250H190V257" stroke="#54677a" stroke-dasharray="5 4" stroke-width="2" fill="none"/><text x="282" y="225" text-anchor="middle" font-size="8">local BMS sensing</text>',
         '<g data-node="BUS" tabindex="0" role="button" aria-label="Inspect CAN bus"><path d="M345 100V430" stroke="#966b00" stroke-width="5"/><path d="M375 100V430" stroke="#2366be" stroke-width="5"/><path d="M345 100H355l3 -6 5 12 5 -12 5 6h2M345 430h10l3 -6 5 12 5 -12 5 6h2" fill="none" stroke="#223548" stroke-width="2"/><text x="385" y="108" font-size="11">120 Ω</text><text x="385" y="439" font-size="11">120 Ω</text><text x="335" y="375" text-anchor="end" fill="#765400">CAN_H</text><text x="385" y="395" fill="#174d94">CAN_L</text></g>']
    info={'BUS':{'name':'One shared high-speed CAN segment','details':'Paired CAN_H/CAN_L; 120-ohm termination across the pair at each end. Broadcast, not point-to-point routing. Ideal wiring illustration, not an electrical solver. Standard arbitration and differential signalling have separate labs.'}}
    for index,name in enumerate(nodes):
        x,y=positions[index];left=x<360;busx=345 if left else 375
        status='TRANSMITTING' if name==active else 'BROADCAST OBSERVER (MODEL)'
        fill='#fff0dd' if name==active else '#e2f3e9'
        edge=x+83 if left else x-83
        high=f'M{edge} {y-5}H345' if left else f'M{edge} {y-5}H381Q375 {y-11} 369 {y-5}H345'
        low=f'M{edge} {y+5}H339Q345 {y-1} 351 {y+5}H375' if left else f'M{edge} {y+5}H375'
        svg.append(f'<path d="{high}" stroke="#966b00" stroke-width="2" fill="none"/><path d="{low}" stroke="#2366be" stroke-width="2" fill="none"/><circle cx="345" cy="{y-5}" r="3" fill="#966b00"/><circle cx="375" cy="{y+5}" r="3" fill="#2366be"/><g data-node="{index}" tabindex="0" role="button" aria-label="Inspect {html.escape(name,quote=True)}"><rect x="{x-83}" y="{y-28}" width="166" height="56" rx="8" fill="{fill}" stroke="#a9430b" stroke-width="{3 if name==active else 1}"/><text x="{x}" y="{y-5}" text-anchor="middle" font-size="11">{html.escape(name)}</text><text x="{x}" y="{y+14}" text-anchor="middle" font-size="9">{status}</text></g>')
        published=[node for node in experiment['nodes'] if node['name']==name]
        info[str(index)]={'name':name,'activity':status,'publishes':[{'id':hex(node['frame_id']),'period_ms':node['period_ms']} for node in published],
            'observed_message':hex(event['frame_id']) if name!=active else 'own transmission; no loopback receipt asserted',
            'responsibility':{'Motor controller':'Controls motor torque/speed; original synthetic engine payload only here.','Battery Management System':'Monitors pack conditions; original synthetic temperature payload only here.','Vehicle Control Unit':'Coordinates vehicle requests; teaching payload is uninterpreted.','Instrument cluster':'Presents driver information; publishes an uninterpreted teaching message.','Brake ECU':'Collects local wheel-speed/brake information; passive CAN observer in this version.'}.get(name,'Educational publisher; not production firmware or vehicle-specific topology.')}
    svg.append('<circle cx="610" cy="202" r="12" fill="#d9e7f0"/><text x="610" y="225" text-anchor="middle" font-size="10">wheel sensor</text><path d="M610 214V380H530V382" stroke="#54677a" stroke-dasharray="5 4" fill="none"/><text x="595" y="245" text-anchor="middle" font-size="9">local ECU link</text>')
    # Wheel-speed sensing terminates at the passive Brake ECU, not a CAN node.
    svg.append(f'<circle class="pulse" cx="360" cy="{positions[nodes.index(active)][1]}" r="10" fill="#a9430b"/><text x="360" y="483" text-anchor="middle" font-size="12">EVENT {event["index"]} · {event["timestamp_ms"]} ms · ID 0x{event["frame_id"]:03X} · {html.escape(event["payload_hex"])}</text></svg>')
    payload=json.dumps(info).replace('<','\\u003c').replace('>','\\u003e')
    animation='animation:pulse 1s ease-out infinite;' if playing and not reduced else ''
    return '''<html><head><style>body{margin:0;font:13px system-ui;color:#162638;background:#f5f6f8}svg{width:100%;max-height:490px}g[data-node]{cursor:pointer}g:focus{outline:3px solid #a9430b}.pulse{'''+animation+'''}@keyframes pulse{from{r:7;opacity:1}to{r:20;opacity:.15}}@media(prefers-reduced-motion:reduce){.pulse{animation:none}}pre{white-space:pre-wrap;background:white;border:1px solid #c1cedb;padding:9px;border-radius:6px;min-height:65px}</style></head><body>'''+''.join(svg)+'''<pre id="info" aria-live="polite">Select an ECU or the paired bus to inspect its role and message activity.</pre><script>const data='''+payload+''';document.querySelectorAll('[data-node]').forEach(n=>{function show(){document.getElementById('info').textContent=JSON.stringify(data[n.dataset.node],null,2)}n.addEventListener('click',show);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show()}})});</script></body></html>'''


def arbitration_html(result,index):
    step=result['steps'][index]
    rows=['<table class="arb-table"><caption>Standard identifier bits, MSB first; outlined column is being compared</caption><thead><tr><th>Transmitter / original ID</th>']
    rows.extend(f'<th>{10-column}</th>' for column in range(11));rows.append('<th>Current status</th></tr></thead><tbody>')
    for node,value in enumerate(result['identifiers']):
        lost=node not in step['active'];status='Lost here' if node in step['lost'] else 'Previously lost' if lost else 'Active'
        rows.append(f'<tr><th>{["Motor controller","BMS","Instrument cluster"][node]}<br/>0x{value:03X}</th>')
        for column,bit in enumerate(result['bits'][node]):
            cls=('compared ' if column==index else '')+('lost' if lost else '')
            rows.append(f'<td class="{cls}">{bit}</td>')
        rows.append(f'<td>{status}</td></tr>')
    rows.append('<tr><th>Observed bus</th>')
    rows.extend(f'<td class="{"compared" if column==index else ""}">{result["steps"][column]["bus"] if column<=index else "·"}</td>' for column in range(11))
    return ''.join(rows)+'</tr></tbody></table>'
