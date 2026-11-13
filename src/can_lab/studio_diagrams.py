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


def topology_html(experiment,event,*,playing=False,reduced=False,theme='light',pulse_period=0.5,fault=None):
    """Original SVG; paths used for wiring and pulses come from the same view model."""
    from .visual_model import visual_event
    view=visual_event(experiment,event)
    period=max(.25,min(2,float(pulse_period)))
    dark=theme=='dark'
    bg,surface,ink,muted,border=('#0b1220','#162235','#edf3fb','#b1c1d4','#536b87') if dark else ('#f5f7fa','#ffffff','#162638','#425a70','#91a4b8')
    cyan,orange,green,purple='#39cce4','#ff9b51','#60dca1','#b89aff'
    svg=['<svg id="vehicle" viewBox="0 0 900 620" role="img" aria-label="Illustrative EV architecture, shared terminated CAN pair, four publishers and passive safety electronics">',
        f'<path d="M320 25Q450 5 580 25Q650 55 650 150V490Q640 580 560 590H340Q260 580 250 490V150Q250 55 320 25Z" fill="{surface}" stroke="{border}" stroke-width="3"/>',
        f'<path d="M325 195Q450 175 575 195L605 305H295Z M295 420H605L580 535H320Z" fill="none" stroke="{border}" stroke-width="2"/>',
        '<path d="M250 105H228v90h22M650 105h22v90h-22M250 455h-22v90h22M650 455h22v90h-22" fill="none" stroke="#43546b" stroke-width="14"/>']
    info={'BUS':{'name':'Shared high-speed CAN segment','details':'CAN_H and CAN_L form one broadcast bus with 120-ohm end terminations. Pulses are schematic, not propagation-time or bitrate simulation. Individual receiver flashes represent observability of the SAME retained frame, not new messages.'}}
    def component(key,label,x,y,detail,width=70,height=30):
        info[key]=detail
        svg.append(f'<g data-node="{key}" role="button" tabindex="0" aria-label="Inspect {html.escape(label,quote=True)}"><title>{html.escape(detail["details"])}</title><rect x="{x-width/2}" y="{y-height/2}" width="{width}" height="{height}" rx="8" fill="{surface}" stroke="{purple}"/><text x="{x}" y="{y+4}" text-anchor="middle" fill="{ink}" font-size="14">{html.escape(label)}</text></g>')
    component('MOTOR','Motor',450,80,{'name':'Traction motor','details':'Illustrative front-drive layout. Local control/power link to motor controller; not an extra CAN publisher.'},85,40)
    component('PACK','HV battery',465,382,{'name':'Battery pack','details':'Illustrative underfloor battery. Dashed local sensing link to BMS; no battery voltage/current model is introduced.'},100,155)
    svg.append(f'<path d="M405 80H300V121M415 382H370V365" stroke="{purple}" stroke-width="2" stroke-dasharray="5 4" fill="none"/>')
    # One conventional segment; stubs cross the other conductor using explicit bridges.
    svg.append(f'<g data-node="BUS" role="button" tabindex="0" aria-label="Inspect CAN bus"><title>CAN_H / CAN_L: differential signalling, shared broadcast and two end terminations</title><path d="M390 125V535" stroke="#cda22a" stroke-width="4"/><path d="M410 125V535" stroke="#5d9df4" stroke-width="4"/><path d="M390 125h4l3 -5 3 10 3 -10 3 5h4M390 535h4l3 -5 3 10 3 -10 3 5h4" stroke="{ink}" fill="none"/><text x="418" y="128" fill="{ink}">120 Ω</text><text x="418" y="543" fill="{ink}">120 Ω</text></g>')
    responsibility={'MCU':'Motor torque/speed control; original synthetic engine payload only here.','BMS':'Pack monitoring; original synthetic temperature message only here.',
        'VCU':'Vehicle coordination; uninterpreted teaching payload.','Cluster':'Driver information; uninterpreted teaching message.',
        'ABS / ESC':'Illustrative local wheel-speed collection and brake/stability role. Passive CAN observer, no ABS firmware.',
        'Airbag':'Illustrative restraint controller and local crash sensing. Passive CAN observer; no crash model or deployment logic.'}
    for node in view['nodes']:
        key,x,y=node['key'],node['x'],node['y']
        for line,color in [('H','#cda22a'),('L','#5d9df4')]:
            svg.append(f'<path id="branch-{key}-{line}" d="{view["paths"][key][line]}" stroke="{color}" stroke-width="2" fill="none"/><circle cx="{390 if line=="H" else 410}" cy="{y+(-5 if line=="H" else 5)}" r="3" fill="{color}"/>')
        status='TX' if node['active'] else 'RX model' if node['publisher'] else 'Passive'
        flagged=bool(fault and fault.get('mapped') and fault.get('exceeded') and node['role']==fault.get('component'))
        if flagged:status='THRESHOLD EVIDENCE'
        stroke='#f07373' if flagged else orange if node['active'] else border if playing and not reduced else green
        receive_set=f'<set attributeName="stroke" to="{green}" begin="{period*.9:.3f}s" fill="freeze"/>' if playing and not reduced and not node['active'] else ''
        svg.append(f'<g data-node="{key}" role="button" tabindex="0" aria-label="Inspect {html.escape(node["name"],quote=True)}"><title>{html.escape(responsibility[node["label"]])}</title><rect x="{x-60}" y="{y-24}" width="120" height="48" rx="8" fill="{surface}" stroke="{stroke}" stroke-width="{3 if node["active"] else 1.5}">{receive_set}</rect><text x="{x}" y="{y-3}" text-anchor="middle" fill="{ink}" font-size="14">{node["label"]}</text><text x="{x}" y="{y+14}" text-anchor="middle" fill="{muted}" font-size="11">{status}</text></g>')
        info[key]={'name':node['name'],'role':node['role'],'details':responsibility[node['label']],
            'activity':status,'fault_evidence':fault if flagged else None,'publishes':[{'id':hex(n['frame_id']),'period_ms':n['period_ms']} for n in experiment['nodes'] if n['name']==node['name']] if node['publisher'] else [],
            'observes':hex(event['frame_id']) if not node['active'] else 'Own transmission; loopback receipt not asserted'}
    # Four local wheel inputs terminate at ABS, never directly on CAN.
    for key,x,y in [('FL',235,155),('FR',665,155),('RL',235,505),('RR',665,505)]:
        component(key,key+' speed',x,y,{'name':key+' wheel-speed sensor','details':'Illustrative local sensor link to ABS/ESC ECU. Not a CAN node or simulated publisher.'},62,25)
        route=f'M{x} {y+13}V{560 if y>400 else 570}H620V479'
        svg.append(f'<path d="{route}" stroke="{purple}" stroke-width="1.5" stroke-dasharray="4 5" fill="none"/>')
    for key,x in [('CRASH_L',485),('CRASH_R',570)]:
        component(key,'Crash',x,215,{'name':'Illustrative crash sensor','details':'Local connection to airbag control unit; no CAN publishing, crash dynamics or deployment simulation.'},55,24)
        svg.append(f'<path d="M{x} 227V280H280V274" stroke="{purple}" stroke-width="1.5" stroke-dasharray="4 5" fill="none"/>')
    # Staged TX -> both directions of the same segment -> receiver stubs.
    period=max(.25,min(2,float(pulse_period)));tx=period*.2;bus=period*.4;rx=period*.4
    animations=[]
    if playing and not reduced:
        def pulse(path,start,duration,color,reverse=False):
            animations.append(f'<circle class="motion" r="4" fill="{color}" opacity="0"><set attributeName="opacity" to="1" begin="{start:.3f}s" dur="{duration:.3f}s"/><animateMotion path="{path}" begin="{start:.3f}s" dur="{duration:.3f}s" fill="freeze" calcMode="linear" keyPoints="{"1;0" if reverse else "0;1"}" keyTimes="0;1"/></circle>')
        active=next(n for n in view['nodes'] if n['active'])
        for line,x,dy in [('H',390,-5),('L',410,5)]:
            pulse(view['paths'][active['key']][line],0,tx,orange)
            for end in (125,535):pulse(f'M{x} {active["y"]+dy}V{end}',tx,bus,cyan)
            for key in view['receivers']:pulse(view['paths'][key][line],tx+bus,rx,green,True)
    svg.extend(animations)
    svg.append(f'<text x="450" y="610" text-anchor="middle" fill="{ink}">EVENT {event["index"]} · {event["timestamp_ms"]} ms · ID 0x{event["frame_id"]:03X} · {event["payload_hex"]}</text></svg>')
    payload=json.dumps(info).replace('<','\\u003c').replace('>','\\u003e')
    motion='true' if playing and not reduced else 'false'
    decoded=html.escape(json.dumps(event.get('decoded',{})))
    return f'''<html><head><style>body{{margin:0;background:{bg};color:{ink};font:12px system-ui}}svg{{width:100%;max-height:540px}}.motion{{pointer-events:none}}g[data-node]{{cursor:pointer}}g[data-node]:focus{{outline:3px solid {orange}}}g[data-node]:hover rect{{stroke:{cyan};stroke-width:2.5}}.legend{{display:flex;flex-wrap:wrap;gap:12px;padding:8px}}.info{{background:{surface};border:1px solid {border};border-radius:8px;padding:10px;white-space:pre-wrap;min-height:68px}}@media(prefers-reduced-motion:reduce){{.motion{{display:none}}}}</style></head><body>'''+''.join(svg)+f'''<div class="legend"><span style="color:{orange}">● TX</span><span style="color:{green}">● Modeled RX</span><span style="color:{purple}">┄ Local sensor/control</span><span>CAN_H gold / CAN_L blue</span><span>Decoded: {decoded}</span></div><div id="info" class="info" aria-live="polite">Select an ECU, sensor or shared bus. Extra safety ECUs are passive illustration. Pulse travel is schematic, not physical timing.</div><script>const data='''+payload+''';document.querySelectorAll('[data-node]').forEach(n=>{function show(){document.getElementById('info').textContent=JSON.stringify(data[n.dataset.node],null,2)}n.addEventListener('click',show);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show()}})});if(!'''+motion+'''||matchMedia('(prefers-reduced-motion: reduce)').matches){document.getElementById('vehicle').pauseAnimations();document.querySelectorAll('.motion').forEach(n=>n.style.display='none')}</script></body></html>'''


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
