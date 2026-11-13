"""Presentation geometry and event mapping only; never creates CAN messages."""
LAYOUT=[('Motor controller','MCU',300,145),('Battery Management System','BMS',300,365),
        ('Vehicle Control Unit','VCU',600,150),('Instrument cluster','Cluster',600,250),
        ('Brake ECU','ABS / ESC',600,455),('Airbag control unit','Airbag',300,250)]


def visual_event(experiment,event):
    if not any(all(row.get(key)==event.get(key) for key in ('index','node','frame_id','payload_hex','timestamp_ms')) for row in experiment['events']):
        raise ValueError('Visual event must reference an unchanged retained event')
    publishers=[node['name'] for node in experiment['nodes']]
    if event['node'] not in publishers:raise ValueError('Transmitter is not a configured publisher')
    nodes=[]
    for index,(role,label,x,y) in enumerate(LAYOUT):
        name=publishers[index] if index<len(publishers) else role
        nodes.append({'key':str(index),'name':name,'role':role,'label':label,'x':x,'y':y,
            'publisher':index<len(publishers),'active':name==event['node'] and index<len(publishers)})
    # The original core has at most four publishers. Extra illustrated nodes stay passive.
    active=next(node for node in nodes if node['active'])
    paths={}
    for node in nodes:
        x,y=node['x'],node['y'];edge=x+60 if x<400 else x-60
        high=f'M{edge} {y-5}H390' if x<400 else f'M{edge} {y-5}H416Q410 {y-11} 404 {y-5}H390'
        low=f'M{edge} {y+5}H384Q390 {y-1} 396 {y+5}H410' if x<400 else f'M{edge} {y+5}H410'
        paths[node['key']]={'H':high,'L':low}
    return {'event_index':event['index'],'transmitter':active['key'],'nodes':nodes,'paths':paths,
            'receivers':[node['key'] for node in nodes if not node['active']],
            'scope':'Schematic broadcast observability; passive safety ECUs and local sensors do not publish messages.'}


def fault_visual(experiment,finding):
    """Explicit publisher-role mapping; retain finding references without guessing."""
    publisher=next((node for node in experiment['nodes'] if node['name']==finding['node']),None)
    if publisher is None or publisher['frame_id']!=0x100 or publisher['name']!='Powertrain ECU':
        return {'mapped':False,'limitation':'No verified visual ECU mapping for this finding; original evidence remains available.'}
    return {'mapped':True,'component':'Motor controller','label':{'missing_message':'Expected release not observed',
        'timing':'Arrival timing deviation','signal_rate':'Synthetic speed discontinuity'}[finding['kind']],
        'exceeded':finding['exceeded'],'evidence_indices':list(finding['evidence_indices']),
        'qualification':'Known synthetic injection / threshold evidence, not an ECU hardware diagnosis.'}
