"""
inject_event.py — Demo Event Injector
Simulate cloud or inverter fault events during the demo.

Usage:
  python scripts/inject_event.py --type=cloud --plant=RJ01 --severity=high
  python scripts/inject_event.py --type=inverter_fault --plant=GJ01
  python scripts/inject_event.py --clear
"""

import argparse, json, os, sys, time

DATA_DIR   = os.environ.get("DATA_DIR", "./data")
EVENT_FILE = os.path.join(DATA_DIR, "injected_events.json")


def inject(plant_id: str, event_type: str, severity: str = "high"):
    os.makedirs(DATA_DIR, exist_ok=True)
    events = {}
    if os.path.exists(EVENT_FILE):
        try:
            with open(EVENT_FILE) as f:
                events = json.load(f)
        except Exception:
            events = {}

    events[plant_id] = {"type": event_type, "severity": severity, "injected_at": time.time()}

    with open(EVENT_FILE, "w") as f:
        json.dump(events, f, indent=2)

    print(f"Event injected: {event_type} (severity={severity}) on {plant_id}")
    print(f"Watch data/dispatch_commands.jsonl and data/operator_advisory.jsonl for response")


def clear_events():
    if os.path.exists(EVENT_FILE):
        os.remove(EVENT_FILE)
    print("All injected events cleared")


def main():
    parser = argparse.ArgumentParser(description="RenewCast Event Injector")
    parser.add_argument("--type",     choices=["cloud", "inverter_fault", "demand_spike"])
    parser.add_argument("--plant",    choices=["RJ01", "GJ01", "TN01"], default="RJ01")
    parser.add_argument("--severity", choices=["low", "medium", "high"],  default="high")
    parser.add_argument("--clear",    action="store_true")
    args = parser.parse_args()

    if args.clear:
        clear_events()
        return
    if not args.type:
        parser.print_help()
        sys.exit(1)

    inject(args.plant, args.type, args.severity)
    print()
    print("To clear:  python scripts/inject_event.py --clear")


if __name__ == "__main__":
    main()
