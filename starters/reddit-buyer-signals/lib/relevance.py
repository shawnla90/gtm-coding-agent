#!/usr/bin/env python3
"""relevance.py - the shared vocabulary and filters for your category's buyer talk.

Used by pull.py (to keep noise and stale threads out of the database at ingest) and by mine.py
(to classify what kind of buyer language each line is). Editing the lists here re-points the whole
engine at a different product or niche.

The example below is a project-management SaaS for small teams (call it "Acme PM"). Swap the
brands, category nouns, and topics for your own market and the engine tracks your buyers instead.
"""
import re

# the tools your buyers compare you against - the vocabulary of the buying decision.
# For Acme PM, these are the project-management apps that show up in every "vs" thread.
BRANDS = [
    "asana", "monday.com", "monday", "trello", "clickup", "notion", "jira", "basecamp",
    "linear", "airtable", "wrike", "todoist", "smartsheet", "height", "motion", "teamwork",
    "ms project", "microsoft project", "shortcut", "hive", "nifty", "meistertask",
]

# topic -> keywords (auto-tag). Tuned for project-management software, not generic B2B.
TOPIC_KEYWORDS = {
    "kanban-boards": ["kanban", "board view", "swimlane", "card view"],
    "gantt-charts": ["gantt", "timeline view", "dependencies", "critical path"],
    "task-management": ["task management", "task tracker", "to-do", "to do list", "checklist"],
    "sprint-planning": ["sprint", "agile", "scrum", "backlog", "story points", "standup"],
    "all-in-one-vs-focused": ["all in one", "all-in-one", "bloated", "too many features", "docs and tasks"],
    "free-vs-paid": ["free plan", "free tier", "pricing", "per seat", "per user", "paywall", "too expensive"],
    "integrations": ["integration", "slack integration", "api", "zapier", "automations", "webhooks"],
    "team-collaboration": ["team collaboration", "remote team", "client collaboration", "shared workspace"],
    "switching-tools": ["switching from", "migrate", "migration", "moving off", "alternative to", "replace"],
    "time-tracking": ["time tracking", "timesheet", "track hours", "billable hours"],
}

# category vocabulary - a thread or quote must be about project-management software, not generic
# Reddit chatter. Rename this list to your own category nouns when you re-point the engine.
CATEGORY = ["project management", "project-management", "pm tool", "pm software", "task management",
            "task tracker", "kanban", "gantt", "sprint", "scrum", "agile", "backlog", "roadmap",
            "workflow", "workspace", "collaboration tool", "productivity app", "to-do list",
            "team management", "ticketing", "issue tracker", "time tracking", "project tracker",
            "task board", "work management"]

PAIN = ["too expensive", "overpriced", "price keeps", "pricing keeps", "bloated", "overkill",
        "clunky", "confusing", "steep learning curve", "frustrat", "hate", "regret", "nightmare",
        "buggy", "slow", "limited", "locked behind", "paywall", "gave up", "switching away"]

COMPARE = [" vs ", " vs.", "versus", "compared to", " or "]

QUESTION_HINTS = ["which", "what ", "should i", "recommend", "worth it", "help", "advice",
                  "looking for", "best ", "better", "thoughts on", "any good", "opinions",
                  "suggestions", "alternative"]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def brands_in(text):
    t = norm(text)
    found = []
    for b in BRANDS:
        if b in t:
            canon = {"monday": "monday.com", "microsoft project": "ms project"}.get(b, b)
            if canon not in found:
                found.append(canon)
    return found


def auto_tags(text):
    t = norm(text)
    return [topic for topic, kws in TOPIC_KEYWORDS.items() if any(k in t for k in kws)]


def is_relevant(text):
    """True only if the text is actually about project-management software - a real tool name or a
    category noun. Generic words (team, remote, work) are NOT enough on their own: they match
    politics, career, and gaming threads a broad keyword search surfaces."""
    t = norm(text)
    return bool(brands_in(t)) or any(c in t for c in CATEGORY)


def classify(text):
    """Return the buyer-language kind, or None if this isn't buyer language."""
    t = norm(text)
    if any(c in t for c in COMPARE) and brands_in(t):
        return "comparison"
    if any(p in t for p in PAIN):
        return "pain"
    if t.endswith("?") or any(h in t for h in QUESTION_HINTS):
        if "recommend" in t or "looking for" in t or "which" in t or "best " in t or "alternative" in t:
            return "recommendation"
        return "question"
    return None
