#!/usr/bin/env python3
"""Read projects.toml (falls back to projects.example.toml) for the builder and the launchers.

As a library:  projects.load() -> list of project dicts with `workflow` lists.
From a shell:  python3 profile/projects.py env <id> [workflow-label]
               prints shell assignments (P_PATH, P_NAME, P_MODEL, P_EFFORT, P_GH_USER,
               P_PROMPT, P_SESSION) for claude-project.command to eval.
"""
import os
import shlex
import sys
import tomllib

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EFFORTS = {"low", "medium", "high", "xhigh", "max"}


def path():
    real = os.path.join(KIT, "projects.toml")
    return real if os.path.exists(real) else os.path.join(KIT, "projects.example.toml")


def load():
    with open(path(), "rb") as f:
        data = tomllib.load(f)
    projects = data.get("project", [])
    seen = set()
    for p in projects:
        for field in ("id", "name", "path"):
            if not p.get(field):
                raise SystemExit("projects.toml: every [[project]] needs %s" % field)
        if p["id"] in seen:
            raise SystemExit("projects.toml: duplicate id %r" % p["id"])
        seen.add(p["id"])
        p["path"] = os.path.expanduser(p["path"])
        p.setdefault("workflow", [])
        for w in [p] + p["workflow"]:
            if w.get("effort") and w["effort"] not in EFFORTS:
                raise SystemExit("projects.toml: effort %r not in %s" % (w["effort"], sorted(EFFORTS)))
    return projects


def find(pid, label=None):
    for p in load():
        if p["id"] == pid:
            if label is None:
                return p, None
            for w in p["workflow"]:
                if w["label"] == label:
                    return p, w
            raise SystemExit("project %r has no workflow %r" % (pid, label))
    raise SystemExit("no project %r in %s" % (pid, path()))


def env(pid, label=None):
    p, w = find(pid, label)
    w = w or {}
    out = {
        "P_PATH": p["path"],
        "P_NAME": p["name"],
        "P_MODEL": w.get("model", p.get("model", "")),
        "P_EFFORT": w.get("effort", p.get("effort", "")),
        "P_GH_USER": p.get("gh_user", ""),
        "P_PROMPT": w.get("prompt", ""),
        "P_SESSION": "%s: %s" % (p["name"], w["label"]) if w else p["name"],
    }
    return "\n".join("%s=%s" % (k, shlex.quote(v)) for k, v in out.items())


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "env":
        print(env(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    else:
        for p in load():
            print("%-10s %-20s %s  [%s]" % (p["id"], p["name"], p["path"],
                                            ", ".join(w["label"] for w in p["workflow"])))
