#!/usr/bin/env python3
"""tasks/linear.py — Linear backend for the tiered task engine (stdlib only).

Linear is the Tier-3 task source (qute-code-kit ADR-0004): all work items live
in Linear; GitHub Issues are an issue record, not a queue. This module gives
pulse.sh the three verbs it needs against the Linear GraphQL API.

Usage:
    linear.py check                     exit 0 if usable (key + team resolvable)
    linear.py list                      open issues for the bound team
    linear.py add "title" [body]        create an issue -> prints identifier + URL
    linear.py close ABC-123 [comment]   move to the team's "completed" state

Auth:  LINEAR_API_KEY env var (a personal API key; sent as the Authorization
       header — Linear personal keys don't use a "Bearer " prefix).
Team:  resolved from the repo's docs/agents/issue-tracker.md marker line
           <!-- qute-tracker: linear team=ABC -->
       or the LINEAR_TEAM_KEY env var (marker wins; see lib.sh).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.linear.app/graphql"


def die(msg: str, code: int = 1) -> "NoReturn":  # noqa: F821
    print(f"linear: {msg}", file=sys.stderr)
    sys.exit(code)


def gql(query: str, variables: dict | None = None) -> dict:
    key = os.environ.get("LINEAR_API_KEY", "")
    if not key:
        die(
            "LINEAR_API_KEY not set — cannot reach Linear. In an orchestrated "
            "workspace (Jimek/Symphony-Elixir) the key is stripped by design: "
            "use the orchestrator's 'linear' tool instead of this backend."
        )
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        die(f"API error {e.code}: {e.read().decode(errors='replace')[:200]}")
    except (urllib.error.URLError, TimeoutError) as e:
        die(f"cannot reach Linear API: {e}")
    if payload.get("errors"):
        die(f"GraphQL error: {payload['errors'][0].get('message', payload['errors'])}")
    return payload["data"]


def repo_root() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.getcwd()


def team_key() -> str:
    """Marker in docs/agents/issue-tracker.md wins; LINEAR_TEAM_KEY is fallback."""
    binding = os.path.join(repo_root(), "docs", "agents", "issue-tracker.md")
    if os.path.isfile(binding):
        with open(binding, encoding="utf-8", errors="replace") as f:
            m = re.search(
                r"<!--\s*qute-tracker:\s*linear\s+team=([A-Za-z0-9_-]+)", f.read()
            )
        if m:
            return m.group(1)
    key = os.environ.get("LINEAR_TEAM_KEY", "")
    if not key:
        die(
            "no team bound — add `<!-- qute-tracker: linear team=ABC -->` to "
            "docs/agents/issue-tracker.md (or set LINEAR_TEAM_KEY)"
        )
    return key


def team_id(key: str) -> str:
    data = gql(
        "query($key:String!){ teams(filter:{key:{eq:$key}}) { nodes { id key } } }",
        {"key": key},
    )
    nodes = data["teams"]["nodes"]
    if not nodes:
        die(f"team '{key}' not found in this Linear workspace")
    return nodes[0]["id"]


def cmd_check() -> None:
    team_id(team_key())
    print("ok")


def cmd_list() -> None:
    key = team_key()
    data = gql(
        """query($key:String!){ issues(
             filter:{ team:{key:{eq:$key}}, state:{type:{nin:["completed","canceled"]}} }
             orderBy: updatedAt, first: 50
           ) { nodes { identifier title state { name } assignee { displayName } } } }""",
        {"key": key},
    )
    nodes = data["issues"]["nodes"]
    if not nodes:
        print(f"no open Linear issues for team {key}")
        return
    for n in nodes:
        who = n["assignee"]["displayName"] if n.get("assignee") else "—"
        print(f"  {n['state']['name']:<12} {n['identifier']:<10} {n['title']}  [{who}]")


def cmd_add(title: str, body: str) -> None:
    tid = team_id(team_key())
    data = gql(
        """mutation($input:IssueCreateInput!){ issueCreate(input:$input) {
             success issue { identifier url } } }""",
        {"input": {"teamId": tid, "title": title, "description": body or None}},
    )
    res = data["issueCreate"]
    if not res["success"]:
        die("issueCreate failed")
    print(f"{res['issue']['identifier']}  {res['issue']['url']}")


def resolve_issue(ref: str) -> dict:
    m = re.fullmatch(r"([A-Za-z0-9_-]+)-(\d+)", ref)
    if not m:
        die(f"'{ref}' is not a Linear identifier (expected e.g. ABC-123)")
    data = gql(
        """query($key:String!,$num:Float!){ issues(
             filter:{ team:{key:{eq:$key}}, number:{eq:$num} }, first: 1
           ) { nodes { id identifier team { id } } } }""",
        {"key": m.group(1).upper(), "num": float(m.group(2))},
    )
    nodes = data["issues"]["nodes"]
    if not nodes:
        die(f"issue {ref} not found")
    return nodes[0]


def cmd_close(ref: str, comment: str) -> None:
    issue = resolve_issue(ref)
    states = gql(
        """query($tid:ID){ workflowStates(filter:{ team:{id:{eq:$tid}}, type:{eq:"completed"} },
             first: 1) { nodes { id name } } }""",
        {"tid": issue["team"]["id"]},
    )["workflowStates"]["nodes"]
    if not states:
        die("no 'completed' workflow state found for the issue's team")
    if comment:
        gql(
            "mutation($input:CommentCreateInput!){ commentCreate(input:$input){ success } }",
            {"input": {"issueId": issue["id"], "body": comment}},
        )
    res = gql(
        "mutation($id:String!,$input:IssueUpdateInput!){ issueUpdate(id:$id,input:$input){ success } }",
        {"id": issue["id"], "input": {"stateId": states[0]["id"]}},
    )["issueUpdate"]
    if not res["success"]:
        die("issueUpdate failed")
    print(f"closed {issue['identifier']} -> {states[0]['name']}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        die("usage: linear.py <check|list|add|close> ...", 2)
    cmd, rest = args[0], args[1:]
    if cmd == "check":
        cmd_check()
    elif cmd == "list":
        cmd_list()
    elif cmd == "add":
        if not rest:
            die('usage: linear.py add "title" [body...]', 2)
        cmd_add(rest[0], " ".join(rest[1:]))
    elif cmd == "close":
        if not rest:
            die("usage: linear.py close ABC-123 [comment...]", 2)
        cmd_close(rest[0], " ".join(rest[1:]))
    else:
        die(f"unknown command '{cmd}'", 2)


if __name__ == "__main__":
    main()
