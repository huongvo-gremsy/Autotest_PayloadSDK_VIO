"""
utils/report.py
───────────────
Renders SuiteResult into HTML, JSON, and plain-text summary reports.
"""

from __future__ import annotations

import json
import shlex
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.runner import SuiteResult, StepResult


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JSON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_json(suite: "SuiteResult", path: str):
    data = {
        "started_at":  suite.started_at.isoformat() if suite.started_at else None,
        "finished_at": suite.finished_at.isoformat() if suite.finished_at else None,
        "duration_s":  round(suite.duration, 2),
        "summary": {
            "total":   suite.total,
            "passed":  suite.passed,
            "failed":  suite.failed,
            "skipped": suite.skipped,
        },
        "steps": [_step_to_dict(r) for r in suite.results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def render_text_summary(suite: "SuiteResult", path: str):
    started = suite.started_at.isoformat() if suite.started_at else "N/A"
    finished = suite.finished_at.isoformat() if suite.finished_at else "N/A"

    lines = [
        "PayloadSDK Test Summary",
        "=" * 40,
        f"Started : {started}",
        f"Finished: {finished}",
        f"Duration: {round(suite.duration, 2)}s",
        "",
        "Summary",
        f"  Total  : {suite.total}",
        f"  Passed : {suite.passed}",
        f"  Failed : {suite.failed}",
        f"  Skipped: {suite.skipped}",
        "",
        "Steps",
    ]

    for result in suite.results:
        line = (
            f"[{result.status}] {result.step.name} | "
            f"duration={round(result.duration, 2)}s | "
            f"attempt={result.attempt} | "
            f"rc={result.return_code}"
        )
        if result.failure_reason and result.failure_reason != "skipped":
            line += f" | reason={result.failure_reason}"
        lines.append(line)

    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _step_to_dict(r: "StepResult") -> dict:
    return {
        "name":           r.step.name,
        "status":         r.status,
        "passed":         r.passed,
        "duration_s":     round(r.duration, 2),
        "return_code":    r.return_code,
        "attempt":        r.attempt,
        "failure_reason": r.failure_reason,
        "tags":           r.step.tags,
        "started_at":     r.started_at.isoformat(),
        "finished_at":    r.finished_at.isoformat(),
        "output_lines":   r.output.count("\n") + 1 if r.output else 0,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_STATUS_COLOR = {"PASS": "#22c55e", "FAIL": "#ef4444", "SKIP": "#94a3b8"}
_STATUS_BG    = {"PASS": "#f0fdf4", "FAIL": "#fef2f2", "SKIP": "#f8fafc"}


def render_html(suite: "SuiteResult", path: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = "\n".join(_step_row(r) for r in suite.results)
    pass_pct = round(suite.passed / suite.total * 100) if suite.total else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Regression Report — {ts}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 40px; border-bottom: 1px solid #1e293b; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.02em; }}
  .header .meta {{ color: #64748b; font-size: 0.85rem; margin-top: 6px; }}
  .summary {{ display: flex; gap: 16px; padding: 24px 40px; flex-wrap: wrap; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px 24px; min-width: 140px; }}
  .card .label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 6px; }}
  .card .value {{ font-size: 2rem; font-weight: 700; line-height: 1; }}
  .card.total  .value {{ color: #94a3b8; }}
  .card.passed .value {{ color: #22c55e; }}
  .card.failed .value {{ color: #ef4444; }}
  .card.skip   .value {{ color: #94a3b8; }}
  .card.dur    .value {{ color: #818cf8; font-size: 1.4rem; }}
  .progress-wrap {{ padding: 0 40px 24px; }}
  .progress-bar {{ height: 6px; background: #1e293b; border-radius: 9999px; overflow: hidden; }}
  .progress-fill {{ height: 100%; background: linear-gradient(90deg, #22c55e, #4ade80); border-radius: 9999px; transition: width 0.4s; }}
  .progress-label {{ font-size: 0.78rem; color: #64748b; margin-top: 6px; }}
  .table-wrap {{ padding: 0 40px 40px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; table-layout: fixed; min-width: 1500px; }}
  thead tr {{ background: #1e293b; }}
  th {{ padding: 10px 14px; text-align: left; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; color: #64748b; border-bottom: 1px solid #334155; white-space: nowrap; }}
  td {{ padding: 12px 14px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  tr:hover td {{ background: #1e293b44; }}
  th.col-idx, td.col-idx {{ width: 16%; }}
  th.col-step, td.col-step {{ width: 38%; }}
  th.col-status, td.col-status {{ width: 5%; }}
  th.col-duration, td.col-duration {{ width: 6%; }}
  th.col-rc, td.col-rc {{ width: 4%; }}
  th.col-tags, td.col-tags {{ width: 6%; }}
  th.col-output, td.col-output {{ width: 35%; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; }}
  .badge-PASS {{ background: #14532d; color: #4ade80; }}
  .badge-FAIL {{ background: #450a0a; color: #f87171; }}
  .badge-SKIP {{ background: #1e293b; color: #64748b; }}
  .step-name {{ font-weight: 600; color: #f1f5f9; }}
  .reason {{ color: #f87171; font-size: 0.8rem; margin-top: 4px; font-family: monospace; }}
  .tags span {{ display: inline-block; background: #1e3a5f; color: #93c5fd; border-radius: 4px; padding: 1px 7px; font-size: 0.68rem; margin-right: 4px; }}
  .dur {{ color: #94a3b8; font-family: monospace; white-space: nowrap; }}
  .rc {{ font-family: monospace; color: #64748b; }}
  details {{ margin-top: 4px; }}
  summary {{ cursor: pointer; color: #64748b; font-size: 0.78rem; }}
  summary:hover {{ color: #94a3b8; }}
  .col-output summary {{ white-space: nowrap; }}
  .col-output pre {{ min-width: 100%; }}
  pre {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px; margin-top: 6px; font-size: 0.75rem; color: #94a3b8; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; max-height: 260px; overflow-y: auto; }}
</style>
</head>
<body>

<div class="header">
  <h1>📡 PayloadSDK Regression Report</h1>
  <div class="meta">Generated {ts} &nbsp;·&nbsp; Duration {round(suite.duration, 1)}s</div>
</div>

<div class="summary">
  <div class="card total"><div class="label">Total</div><div class="value">{suite.total}</div></div>
  <div class="card passed"><div class="label">Passed</div><div class="value">{suite.passed}</div></div>
  <div class="card failed"><div class="label">Failed</div><div class="value">{suite.failed}</div></div>
  <div class="card skip"><div class="label">Skipped</div><div class="value">{suite.skipped}</div></div>
  <div class="card dur"><div class="label">Duration</div><div class="value">{round(suite.duration, 1)}s</div></div>
</div>

<div class="progress-wrap">
  <div class="progress-bar"><div class="progress-fill" style="width:{pass_pct}%"></div></div>
  <div class="progress-label">{pass_pct}% pass rate ({suite.passed}/{suite.total})</div>
</div>

<div class="table-wrap">
<table>
<thead>
<tr>
  <th class="col-idx">#</th>
  <th class="col-step">Step</th>
  <th class="col-status">Status</th>
  <th class="col-duration">Duration</th>
  <th class="col-rc">RC</th>
  <th class="col-tags">Tags</th>
  <th class="col-output">Output</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</div>

</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _step_row(r: "StepResult") -> str:
    import html as html_mod
    idx = _command_name(r.step.command)

    tags_html = "".join(f"<span>{t}</span>" for t in r.step.tags) if r.step.tags else "—"
    reason_html = f'<div class="reason">✗ {html_mod.escape(r.failure_reason)}</div>' if r.failure_reason and r.failure_reason != "skipped" else ""

    output_escaped = html_mod.escape(r.output or "(no output)")
    output_html = (
        f"<details><summary>show output ({r.output.count(chr(10))+1 if r.output else 0} lines)</summary>"
        f"<pre>{output_escaped}</pre></details>"
    ) if r.output else "—"

    rc_display = str(r.return_code) if r.return_code is not None else "—"

    return f"""<tr>
  <td class="rc col-idx">{html_mod.escape(str(idx))}</td>
  <td class="col-step">
    <div class="step-name">{html_mod.escape(r.step.name)}</div>
    {reason_html}
    {"<div style='color:#64748b;font-size:0.78rem'>attempt " + str(r.attempt) + "</div>" if r.attempt > 1 else ""}
  </td>
  <td class="col-status"><span class="badge badge-{r.status}">{r.status}</span></td>
  <td class="dur col-duration">{round(r.duration, 2)}s</td>
  <td class="rc col-rc">{rc_display}</td>
  <td class="tags col-tags">{tags_html}</td>
  <td class="col-output">{output_html}</td>
</tr>"""


def _command_name(command: str | list) -> str:
    parts = command if isinstance(command, list) else shlex.split(command)
    if not parts:
        return "—"
    return Path(parts[0]).name
