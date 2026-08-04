# Gotchas: week 01, roster sync

What broke on this project, why, what fixed it, and what caught it. One log per project, and this
one is week 01's.

Newest entry at the top. Every entry is a dated H3 with the same five fields, and none of them are
optional. I write the entry the day it happens, before I know how the story ends, because the
version I wrote while I was still confused is the honest one and it is the one worth reading. I
never rewrite an old entry.

**Caught** is the field that matters. It is the record of me checking my own work before it reached
a real person, and it is the thing this format exists to demonstrate. When nothing caught it and the
user found it first, that goes in the field instead. Those entries are worth more than the clean
ones.

Three rules I set in week 1 and have not broken: paste the real error string, state the time cost
specifically including the part I wasted, and file one entry per break.

---

### 2026-02-14 Caught my OAuth token staged for a commit to a public repo

**What broke:** nothing yet, which is the point. `git status --short` before a Saturday morning
commit came back with `A  sync.py`, `A  token.json`, `M  README.md`. A live Google token, staged, one
`git commit` away from a public repo.
**Why:** the Google auth helper writes `token.json` into the current working directory by default,
so it landed in the project root next to my code on Tuesday and I stopped seeing it. My `.gitignore`
had `.env` and `data/` in it, because those are the two things every tutorial tells you to ignore,
and nothing about tokens. Then `git add .` did what `git add .` does. A default path plus an
incomplete ignore file plus a habit.
**The fix:** `git rm --cached token.json`, then `token.json`, `credentials.json`, `client_secret*.json`
and `*.pickle` into `.gitignore`. Then two things I did not have to do and did anyway: revoked the
token from the Google account permissions page and minted a new one, because "it never got pushed"
is an assumption and revoking took ninety seconds; and moved the file out of the repo entirely with
`TOKEN_PATH = os.environ.get("GTM_GOOGLE_TOKEN", ...)` so the default path stops being a trap.
Nothing secret has a default location inside a folder git can see. That is a rule now rather than a
lesson.
**Caught:** reading `git status` before every commit, which I had been doing out of habit rather
than intention. The habit is the only reason this is a gotcha instead of an incident. It is also the
reason I now read the file list out loud before I type the commit message.
**Cost:** 20 minutes, and it would have cost me the whole semester's repo if I had run `git commit
-am` on autopilot. A public repo with a live credential in the history is a first impression that no
amount of good code walks back.

---

### 2026-02-12 The script exited 0 and put 23 duplicate people in the club's live roster

**What broke:** the run finished with exit code 0 and a clean summary line that said
`[sync] read 64 responses, appended 64, skipped 0`. The roster went from 312 rows to 376. Twenty
three of those new rows were people who were already on it.
**Why:** the dedupe compared the form's email column against the roster's email column with `==`,
and both came back from the API as raw strings exactly as typed by a human into a phone. Twenty
three of the 64 differed from their roster entry by capitalization, a trailing space, or both:
`"A.Member@example.edu "` from the form against `"a.member@example.edu"` on the roster. Two different
strings, one real person, and Python was right. The deeper problem was that I pointed the first live
run at the only copy of a roster six years of officers had built, with no backup and no way to
preview what it was about to do.
**The fix:** `def dedupe_key(email): return email.strip().lower()`. The two rules that came out of it
matter more than the one-liner and are now in every script I write: `--dry-run` is the default and
writing requires `--write` typed on purpose, and the target tab gets snapshotted to a dated backup
tab before any write. Four lines, runs every time.
**Caught:** nothing caught it. The club's VP of membership found it, on a Thursday, in their own
roster. `skipped 0` was the line that should have stopped me and I read it as good news, which is
the part I keep thinking about. The dry-run flag exists because of this entry, and it exists so that
the next version of this mistake happens to a printed line instead of to a person.
**Cost:** 25 minutes to fix, 40 minutes to take 23 rows back out of a live roster by hand on a
Thursday night, one at a time, which is exactly the manual work I built the script to end. Plus one
apology in the club Slack. The apology was the cheap part.

---

### 2026-02-10 The token had the old scopes and never asked me for the new ones

**What broke:** the read side of the club sync worked all morning. The first line that tried to
write threw `gspread.exceptions.APIError: {'code': 403, 'status': 'PERMISSION_DENIED', 'message':
'Request had insufficient authentication scopes.'}`. I re-ran the auth flow three times, the browser
opened, I clicked approve, and the script came back with the same 403.
**Why:** I started with `spreadsheets.readonly` in `SCOPES` while I was only reading, then widened it
to `spreadsheets` when I needed to append. But `token.json` from the first run was still valid and
still carried the read-only scope, and the library uses a valid cached token instead of starting a
new consent flow. The flow I thought I was re-running never actually ran, and the browser window
opening was Google recognizing a session rather than granting anything. The scope lives in the
token, not in the script.
**The fix:** `rm token.json`, then re-run. The consent screen came back with a different list of
permissions on it, which was the tell I had been missing all morning. Then a permanent guard:
`print(f"[auth] scopes on this token: {creds.scopes}")` at startup, on every script I write.
**Caught:** the guard line is what catches it now, in about two seconds. Before I added it I had no
way to see the difference between the credential on disk and the constant in my code, and they had
been different for two hours.
**Cost:** 2 hours 10 minutes, about 90 of those in the Google Cloud console checking project
permissions and enabled APIs, which was the wrong place to look the entire time. The error says
"scopes" and I read it as "permissions", and those are two different things that sound like the same
word.
