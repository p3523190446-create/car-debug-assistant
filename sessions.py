"""Sequence analysis; unknown samples never close a previous incident."""
from diagnostics import diagnose,demo_snapshot

def inspect_session(snapshots, source='import'):
    if not isinstance(snapshots,list) or not 1<=len(snapshots)<=200:
        raise ValueError('一次回放需要1至200份状态快照')
    frames=[];events=[];pending={}
    for i,snapshot in enumerate(snapshots):
        report=diagnose(snapshot,source)
        for finding in report['findings']:
            code=finding['code'];domain=code.split('_',1)[0]
            if finding['level']=='issue':
                if code not in pending:
                    pending[code]=i
                    events.append(dict(frame=i,kind='opened',code=code,title=finding['title']))
            elif code in ('link_ok','line_ok'):
                for old in list(pending):
                    if old.startswith(domain+'_'):
                        events.append(dict(frame=i,kind='recovered',code=old,opened_at=pending.pop(old),title=('通信' if domain=='link' else '巡线数据')+'恢复'))
        frames.append(report)
    return dict(source=source,frames=frames,events=events,unresolved=list(pending),
                summary=dict(frame_count=len(frames),opened=sum(e['kind']=='opened' for e in events),recovered=sum(e['kind']=='recovered' for e in events)),
                note='快照回放用于核对状态变化；恢复需后续对应数据有效，未知不会当作恢复。')

def demo_session():
    return [demo_snapshot('restored'),demo_snapshot('line-stale'),{},demo_snapshot('restored'),demo_snapshot('offline'),demo_snapshot('restored')]
