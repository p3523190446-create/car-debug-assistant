"""Generate reproducible synthetic snapshots, not physical measurements."""
import json
import math
from pathlib import Path
import random
import sys

SEED = 20261030

def generate():
    rng = random.Random(SEED)
    snapshots = []
    last_raw = None
    for i in range(120):
        stage = ('normal' if i < 20 else 'line_stalled' if i < 44 else
                 'missing_fields' if i < 48 else 'line_restored' if i < 72 else
                 'disconnected' if i < 96 else 'link_restored')
        # Relative time only: no invented real capture date or device identity.
        frame = {'simulation': {'synthetic': True, 'seed': SEED,
                 'time_ms': i * 500, 'stage': stage}}
        if stage == 'missing_fields':
            snapshots.append(frame)
            continue
        if stage not in ('line_stalled', 'disconnected'):
            center = 3.5 + math.sin(i / 9) * .8
            last_raw = [max(0, min(4095, round(240 + 2900 *
                        math.exp(-((j - center) / .75) ** 2) + rng.gauss(0, 18))))
                        for j in range(8)]
        connected = stage != 'disconnected'
        sensor_age = (1700 + (i-20)*500 if stage == 'line_stalled' else
                      550 + (i-72)*500 if not connected else rng.randint(25, 130))
        frame.update(connected=connected,
                     link_age_ms=rng.randint(20, 85) if connected else 3200+(i-72)*500,
                     age_ms=rng.randint(30, 150),
                     line={'valid': True, 'age_ms': sensor_age, 'raw': last_raw[:],
                           'digital_mask': sum(1 << j for j, v in enumerate(last_raw) if v < 1500)},
                     capabilities={'drive_control': True})
        snapshots.append(frame)
    return snapshots

if __name__ == '__main__':
    path = Path(__file__).with_name('simulated-sequence.json')
    data = generate()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    sys.path.insert(0, str(path.parent.parent))
    from sessions import inspect_session
    result = inspect_session(data, 'import')
    assert result['summary'] == {'frame_count': 120, 'opened': 2, 'recovered': 2}
    assert not result['unresolved']
    assert all(result['frames'][i]['status'] == 'unknown' for i in range(44, 48))
    assert data[19]['line']['raw'] == data[43]['line']['raw']
    print(json.dumps({'file': str(path), 'synthetic': True, 'seed': SEED,
                      'summary': result['summary'], 'events': result['events']}, ensure_ascii=False, indent=2))
