#!/bin/bash
# Watch all output streams live in terminal. Run in a separate window.
echo "Watching RenewCast outputs... (Ctrl+C to stop)"
echo ""
tail -f data/dispatch_commands.jsonl \
        data/operator_advisory.jsonl \
        data/anomaly_reports.jsonl 2>/dev/null | \
python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('{'):
        continue
    try:
        d  = json.loads(line)
        pid = d.get('plant_id','???')
        ts  = d.get('timestamp','')[-8:-3]
        if 'advisory' in d:
            print(f'[{ts}] ADVISORY  [{pid}]: {d[\"advisory\"][:130]}...')
        elif 'report' in d:
            print(f'[{ts}] ANOMALY   [{pid}]: {d[\"report\"][:130]}...')
        elif 'selected_asset' in d:
            a = d.get('selected_asset','none')
            mw = d.get('allocated_mw',0)
            mc = d.get('cerc_merit_class','?')
            print(f'[{ts}] DISPATCH  [{pid}]: {a} {mw:.1f}MW  CERC-{mc}')
    except Exception:
        pass
"
