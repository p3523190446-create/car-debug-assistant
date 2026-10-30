"""Evidence-based, read-only diagnostics for the existing CH32 status schema."""
import math
from datetime import datetime, timezone

def number(x):
    return type(x) in (int, float) and math.isfinite(x) and x >= 0

def diagnose(data, source='import'):
    if not isinstance(data, dict):
        raise ValueError('状态必须是 JSON 对象')
    if source not in ('demo', 'live', 'import'):
        raise ValueError('来源无效')
    findings=[]
    def add(code, level, title, evidence, explanation, steps):
        findings.append(dict(code=code,level=level,title=title,evidence=evidence,explanation=explanation,steps=steps))
    connected=data.get('connected')
    # Communication age and sensor-group age must never renew each other.
    link_age=data.get('link_age_ms', data.get('age_ms'))
    link_fresh=connected is True and number(link_age) and link_age < 3000
    if connected is False:
        add('link_offline','issue','主控连接已中断',['connected = false'],
            '状态接口报告主控未连接，不能据此判定是线缆、供电还是程序故障。',
            ['查看原控制台是否也显示断连。','由本人检查USB连接与主控供电，再刷新状态；不要直接加大电机输出。'])
    elif connected is not True or not number(link_age):
        add('link_unknown','unknown','连接新鲜度无法确认',[f'connected = {connected}',f'link_age_ms = {link_age}'],
            '连接状态或数据年龄缺失，暂不把它当作在线。',['从原控制台重新取得完整状态JSON。'])
    elif not link_fresh:
        add('link_stale','issue','主控通信数据已过期',[f'link_age_ms = {link_age} ms','阈值：小于3000 ms'],
            '接口仍报告已连接，但主控通信没有及时更新。',['核对原控制台更新时间与通信日志。','检查后重新读取，年龄恢复到阈值内才视为恢复。'])
    else:
        add('link_ok','ok','主控通信正在更新',[f'connected = true',f'link_age_ms = {link_age} ms'],
            '本次快照的通信数据处于有效时间内。',['继续检查巡线数据与控制能力；通信正常不代表所有传感器正常。'])
    line=data.get('line')
    if not link_fresh:
        add('line_unknown','unknown','巡线状态暂不判断',['主控通信未确认新鲜'],
            '保留传感器独立判断，断连时旧读数不能作为当前证据。',['先恢复主控通信，再核对巡线数据。'])
    elif not isinstance(line,dict):
        add('line_missing','unknown','没有巡线数据组',['line 字段缺失或为空'],
            '可能未启用、固件未提供或尚未取得数据；不能直接断言传感器损坏。',['确认原固件支持八路巡线，并查看原控制台能否取得读数。'])
    else:
        age=line.get('age_ms'); raw=line.get('raw'); mask=line.get('digital_mask')
        shape=isinstance(raw,list) and len(raw)==8 and all(type(v) is int and 0<=v<=65535 for v in raw)
        mask_ok=type(mask) is int and 0<=mask<=255
        if number(age) and age>=1500:
            add('line_stale','issue','巡线传感器数据已过期',[f'line.age_ms = {age} ms','有效条件：小于1500 ms'],
                '主控通信可正常更新，但这组传感器数据已经过期。尚不能确定具体根因。',
                ['在原控制台检查八路数据是否持续刷新。','由本人核对传感器供电与串口连接；恢复后重新读取。'])
        elif not number(age) or line.get('valid') is not True or not shape or not mask_ok:
            add('line_invalid','unknown','巡线数据尚不满足有效条件',
                [f'line.valid = {line.get("valid")}',f'line.age_ms = {age}',f'八路数值格式有效 = {shape}',f'数字掩码有效 = {mask_ok}'],
                '缺失、无效或格式异常的数据不用于判断黑线位置。',['先在原控制台取得有效的八路原始值、数字掩码和数据年龄。'])
        else:
            add('line_ok','ok','八路巡线数据正在更新',[f'line.age_ms = {age} ms',f'raw = {raw}',f'digital_mask = {mask}'],
                '这表示读数格式和新鲜度通过检查，现场标定、方向与巡线行驶仍需单独验证。',['检查黑带/地砖采样与标定结果，再按原流程做后续验收。'])
    caps=data.get('capabilities') or {}
    if not isinstance(caps,dict): caps={}
    # drive_control is capability, NOT a motion permit. Never infer a ground permit.
    cap=caps.get('drive_control')
    if cap is False and link_fresh:
        add('drive_unavailable','notice','当前接口未开放遥控能力',['capabilities.drive_control = false'],
            '这是接口能力标记，不能将它等同于CH32地面运动许可，也不能据此判断电机故障。',
            ['查看原控制台的模式和启用条件；由本人按原项目流程核对。'])
    elif cap is True and link_fresh:
        add('drive_available','notice','接口报告支持遥控',['capabilities.drive_control = true'],
            '只证明接口能力标记为真；没有证明CH32运动许可、实际动作或停车验收通过。',['实际控制仍使用原控制台与原验收流程。'])
    else:
        add('drive_unknown','unknown','遥控能力无法确认',['capabilities.drive_control 未确认或通信过期'],
            '没有足够证据解释不能启动的全部原因。',['补齐新鲜能力字段；不能把字段缺失当作许可关闭。'])
    issues=[f for f in findings if f['level']=='issue']
    unknowns=[f for f in findings if f['level']=='unknown']
    actions=[f for f in findings if f['code']=='drive_unavailable']
    status='issue' if issues else 'unknown' if unknowns else 'notice' if actions else 'checked'
    lead=(issues or unknowns or actions or findings)[0]
    return dict(source=source,at=datetime.now(timezone.utc).isoformat(),status=status,
                title=lead['title'] if status!='checked' else '已检查的数据项当前有效',
                findings=findings,issue_codes=[f['code'] for f in issues],
                limits='规则诊断，只解释可观测状态；不推断唯一根因，不判定车辆可安全行驶。')

def answer(report, question):
    if not isinstance(question,str) or not question.strip():
        raise ValueError('请先输入问题')
    q=question.strip()
    if any(s in q for s in ('启动','不动','电机','许可','运行')):
        selected=[f for f in report['findings'] if f['level']=='issue' or f['code'].startswith('drive_')]
    elif any(s in q for s in ('巡线','传感器','黑线','八路')):
        selected=[f for f in report['findings'] if f['code'].startswith('line_')]
    elif any(s in q for s in ('连接','通信','断线','USB','usb')):
        selected=[f for f in report['findings'] if f['code'].startswith('link_')]
    elif any(s in q for s in ('状态','问题','恢复','检查','正常')):
        selected=[f for f in report['findings'] if f['level']!='ok'] or report['findings'][:2]
    else:
        return '当前只支持根据快照解释连接、巡线和遥控能力。这个问题无法从现有字段判断，请换成具体状态问题。'
    return '\n\n'.join(f['title']+'。'+f['explanation']+'\n依据：'+'；'.join(f['evidence'])+'\n下一步：'+' '.join(f['steps']) for f in selected)+'\n\n'+report['limits']

def demo_snapshot(name):
    if name=='unknown': return {}
    data=dict(connected=True,link_age_ms=50,age_ms=100,
              line=dict(valid=True,age_ms=90,raw=[240,245,260,3100,3050,260,240,235],digital_mask=231),
              capabilities=dict(drive_control=True))
    if name=='offline': data.update(connected=False,link_age_ms=6200)
    elif name=='line-stale': data['line'].update(valid=False,age_ms=4600)
    elif name=='capability': data['capabilities']['drive_control']=False
    elif name!='restored': raise ValueError('未知示例')
    return data
