"""deep_sweep — Layer 3 of the event-driven audit model (obsidian-vaults#167).

The WEEKLY DEEP SWEEP: a thin, LLM-free scheduler that runs `audit --deep`
(deps + secrets + static + hygiene) over the LIVE/active repos from the
cross-host inventory, live-capital first. It replaces the old blind daily /cso
round-robin (one project/run, core-only, ~$6/run LLM) with a single cheap
deterministic pass — the audit *verb* owns all the scanning logic, this file
only picks the order and writes a report.

SCOPE (v1): scans repos on the LOCAL host. Remote (ssh) hosts in the inventory
are enumerated but reported unscanned with a reason — run this sweep on each host
(the verb is portable) rather than expecting one host to scan another.

Priority (Tom-approved 2026-07-10): live-capital repos are swept FIRST so a
finding on money-moving code surfaces before the long tail. The order comes from
the `priority` key in audit-inventory.json (or --priority); everything else
follows alphabetically. (The older issue-body wording "over cold repos" is
superseded by the approved 3-layer plan: sweep live/active, prioritize live-capital.)

CLI:
    deep_sweep.py [--config PATH] [--roots a,b] [--host NAME]
                  [--priority a,b] [--limit N] [--report DIR] [--json]

Exit: 0 = all swept repos clean · 1 = findings in at least one repo ·
      2 = nothing swept (empty inventory) or every repo failed to scan.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402
import repo_inventory  # noqa: E402


def order_repos(repos: list[dict], priority: list[str]) -> list[dict]:
    """Live-capital first (in the given order), then the rest alphabetically."""
    rank = {name: i for i, name in enumerate(priority)}
    prioritized = [r for r in repos if r["name"] in rank]
    prioritized.sort(key=lambda r: rank[r["name"]])
    rest = sorted((r for r in repos if r["name"] not in rank), key=lambda r: r["name"])
    return prioritized + rest


def sweep_one(repo: dict) -> dict:
    """Run `audit --deep` on one repo path; return a compact per-repo record.

    LOCAL-HOST ONLY (v1): the audit verb scans the local filesystem, so a repo
    discovered on a REMOTE ssh host in the inventory cannot be scanned from here
    and is reported unscanned with an explicit reason (never a clean pass). Deep
    sweeping remote hosts is a follow-up: run this same sweep ON each host (the
    verb is portable), or teach it to `ssh <host> audit --deep`.
    """
    host = repo.get("host", "local")
    # Decide remote-vs-local from the INVENTORY (host identity), before touching the
    # filesystem — a remote path that happens to also exist locally must NOT be
    # scanned as if it were the remote repo (that would silently scan the wrong tree).
    if host and host != "local":
        return {
            "name": repo["name"],
            "path": repo["path"],
            "host": host,
            "exit_code": 2,
            "counts": audit._empty_counts(),
            "error": (
                "remote host — deep_sweep v1 scans the local filesystem only; "
                "run the sweep on that host"
            ),
        }
    root = Path(repo["path"]).resolve()
    if not root.is_dir():
        return {
            "name": repo["name"],
            "path": str(root),
            "host": host,
            "exit_code": 2,
            "counts": audit._empty_counts(),
            "error": "path not readable",
        }
    scanners, counts, exit_code = audit.run_audit(root, deep=True)
    return {
        "name": repo["name"],
        "path": str(root),
        "host": repo.get("host", "local"),
        "exit_code": exit_code,
        "counts": counts,
        "scanners": {n: audit._public_scanner(s) for n, s in scanners.items()},
    }


def run_sweep(
    *,
    config_path: Path | None,
    cli_roots: list[str] | None,
    only_host: str | None,
    priority: list[str] | None,
    limit: int | None,
) -> dict:
    # Route the audit verb's in-process progress chatter to stderr so it never
    # corrupts our stdout product (the --json summary or the markdown report).
    audit._JSON_MODE = True

    inv = repo_inventory.build_inventory(
        cli_roots=cli_roots, only_host=only_host, config_path=config_path
    )
    config = repo_inventory.load_config(config_path)
    prio = priority if priority is not None else list(config.get("priority", []))
    repos = order_repos(inv["repos"], prio)
    if limit:
        repos = repos[:limit]

    results = [sweep_one(r) for r in repos]
    findings = sum(r["counts"]["total"] for r in results)
    unscannable = sum(1 for r in results if r["exit_code"] == 2)

    # Precedence: findings dominate (1); otherwise ANY repo we could not scan is a
    # non-clean outcome (2) — a security sweep must not report "all clear" while a
    # repo was silently skipped; only an all-scanned, finding-free run is 0.
    if findings > 0:
        exit_code = 1
    elif unscannable > 0:
        exit_code = 2
    else:
        exit_code = 0

    return {
        "verb": "deep_sweep",
        "swept": len(results),
        "unscannable": unscannable,
        "priority": prio,
        "findings_total": findings,
        "exit_code": exit_code,
        "repos": results,
    }


def render_report(summary: dict, when: str) -> str:
    lines = [
        f"# Weekly deep audit sweep — {when}",
        "",
        f"Swept **{summary['swept']}** repo(s); "
        f"**{summary['findings_total']}** total finding(s). "
        f"Priority: {', '.join(summary['priority']) or '(none)'}.",
        "",
        "| repo | host | crit | high | med | low | total | verdict |",
        "|---|---|--:|--:|--:|--:|--:|---|",
    ]
    verdicts = {0: "clean", 1: "findings", 2: "could not scan"}
    # Worst first: findings, then unscannable, then clean.
    order = {1: 0, 2: 1, 0: 2}
    for r in sorted(summary["repos"], key=lambda x: order.get(x["exit_code"], 3)):
        c = r["counts"]
        lines.append(
            f"| {r['name']} | {r['host']} | {c['critical']} | {c['high']} | "
            f"{c['medium']} | {c['low']} | {c['total']} | "
            f"{verdicts.get(r['exit_code'], '?')} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deep_sweep", description="Weekly deep audit sweep over live repos."
    )
    parser.add_argument("--config", default=None, help="audit-inventory.json path")
    parser.add_argument(
        "--roots", default=None, help="comma/colon-separated local roots"
    )
    parser.add_argument(
        "--host", default=None, help="limit to a single configured host"
    )
    parser.add_argument(
        "--priority", default=None, help="comma-separated repo names, swept first"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="cap repos swept this run"
    )
    parser.add_argument(
        "--report", default=None, help="dir to write a markdown report into"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the summary as JSON on stdout"
    )
    args = parser.parse_args(argv)

    summary = run_sweep(
        config_path=Path(args.config) if args.config else None,
        cli_roots=repo_inventory._split_roots(args.roots) if args.roots else None,
        only_host=args.host,
        priority=repo_inventory._split_roots(args.priority) if args.priority else None,
        limit=args.limit,
    )

    when = datetime.now().strftime("%Y-%m-%d")
    if args.report:
        report_dir = Path(args.report)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{when}-deep-sweep.md"
        report_path.write_text(render_report(summary, when))
        print(f"deep_sweep: report → {report_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(summary))
    else:
        print(render_report(summary, when))

    return summary["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
