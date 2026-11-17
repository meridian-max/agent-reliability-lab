import argparse
import html
import json
from pathlib import Path

from .core import evaluate, load_jsonl, write_jsonl
from .demo import make_cases, oracle_traces, flawed_traces


def save_report(report, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    rows = "".join(f"<tr><td>{html.escape(r['id'])}</td><td>{r['passed']}</td>"
                   f"<td>{html.escape(', '.join(r['errors'] + r['critical']))}</td></tr>"
                   for r in report["results"])
    path.with_suffix(".html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Agent reliability report</title>"
        "<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}"
        "td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}table{border-collapse:collapse}</style>"
        f"<h1>Agent reliability report</h1><p>{report['passed']}/{report['total']} contracts passed. "
        f"Critical failures: {report['critical_failures']}. Release gate: {report['release_gate']}.</p>"
        "<p>Fixture contract checks do not establish model quality or production safety.</p>"
        f"<table><tr><th>Case</th><th>Passed</th><th>Failure reasons</th></tr>{rows}</table>")


def main():
    parser = argparse.ArgumentParser(description="Evaluate agent decision traces offline")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--output", type=Path, default=Path("runs/demo"))
    run = commands.add_parser("evaluate")
    run.add_argument("--cases", required=True)
    run.add_argument("--traces", required=True)
    run.add_argument("--split", choices=["dev", "test"])
    run.add_argument("--minimum-pass-rate", type=float, default=1.0)
    run.add_argument("--output", type=Path, default=Path("runs/report.json"))
    args = parser.parse_args()
    if args.command == "demo":
        args.output.mkdir(parents=True, exist_ok=True)
        cases = make_cases()
        write_jsonl(args.output / "cases.jsonl", cases)
        for label, traces in [("oracle", oracle_traces(cases)), ("faulty", flawed_traces(cases))]:
            write_jsonl(args.output / f"{label}.jsonl", traces)
            report = evaluate(cases, traces)
            save_report(report, args.output / f"{label}-report.json")
            print(f"{label}: {report['passed']}/{report['total']}; critical={report['critical_failures']}")
        return 0
    report = evaluate(load_jsonl(args.cases), load_jsonl(args.traces), args.split, args.minimum_pass_rate)
    save_report(report, args.output)
    print(json.dumps({k: v for k, v in report.items() if k not in ('results', 'slices')}, indent=2))
    return 0 if report["release_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
