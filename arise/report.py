"""Portable HTML experiment report with escaped evidence and claim statements."""

from html import escape
import json


def render_report(result: dict) -> str:
    def cell(value):
        return escape(str(value))

    metrics = "".join(
        f'<tr><th scope="row">{cell(key)}</th><td>{value:.4f}</td></tr>'
        for key, value in result["metrics"].items()
    )
    claims = "".join(
        "<tr>"
        + "".join(
            f"<td>{cell(value)}</td>"
            for value in (
                claim["id"],
                claim["statement"],
                claim["status"],
                claim["state"],
                claim["confidence"],
                ", ".join(claim["depends_on"]),
            )
        )
        + "</tr>"
        for claim in result["graph"]["claims"]
    )
    evidence = "".join(
        f'<li><strong>{cell(item["id"])}</strong> — {cell(item["statement"])} <small>({cell(item["source"])}, {cell(item["status"])})</small></li>'
        for item in result["graph"]["evidence"]
    )
    rounds = "".join(
        f'<details><summary>Round {item["round"]}</summary><pre>{cell(json.dumps(item, indent=2))}</pre></details>'
        for item in result.get("rounds", [])
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARISE · {cell(result['scenario'])}</title>
<style>body{{font:16px/1.6 system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;color:#182c37}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #cbd5df;padding:.6rem;text-align:left;vertical-align:top}}th{{background:#eaf0f3}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}small{{color:#465768}}.scroll{{overflow:auto}}</style>
<h1>ARISE: {cell(result['scenario'])}</h1><p>Policy: {cell(result.get('policy', 'revision'))}. Deterministic, scenario-driven belief revision.</p>
<h2>Metrics</h2><table><tbody>{metrics}</tbody></table>
<h2>Claims</h2><div class="scroll"><table><thead><tr><th>ID</th><th>Statement</th><th>Epistemic status</th><th>State</th><th>Confidence</th><th>Dependencies</th></tr></thead><tbody>{claims}</tbody></table></div>
<h2>Evidence</h2><ul>{evidence}</ul><h2>Round trace</h2>{rounds}</html>"""
