import os
import sys
import json
from prettytable import PrettyTable
from app.core.config import settings

def view_traces():
    trace_file = os.path.join(settings.TRACE_DIR, "otel", "traces.jsonl")
    if not os.path.exists(trace_file):
        print(f"No traces found at {trace_file}")
        return

    table = PrettyTable()
    table.field_names = ["Trace ID", "Span Name", "Status", "Duration (ms)"]

    with open(trace_file, "r") as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                table.add_row([
                    data.get("trace_id", "")[:8] + "...", 
                    data.get("name", ""), 
                    data.get("status", ""), 
                    f"{data.get('duration_ms', 0.0):.2f}"
                ])
            except json.JSONDecodeError:
                continue

    print(table)

if __name__ == "__main__":
    view_traces()
