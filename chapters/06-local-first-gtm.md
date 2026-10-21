# Chapter 06: Local-First GTM

**Your Mac is a GTM server. Not a metaphor. It has a task scheduler, a database engine, a scripting runtime, and a file system that syncs with git. Stop paying monthly rent for things your laptop already does.**

---

## What "Local-First" Means

Local-first means your data, scripts, and automations live on your machine first. The cloud is a tool you reach out to — for API calls, for email sends, for deployments — but the brain of your GTM operation sits on hardware you own.

This isn't a philosophical stance. It's a practical one:

- **Your prospect list never lives on someone else's server.** No SaaS vendor can get breached and leak your contacts.
- **You don't lose access when you cancel a subscription.** Your data is files on your disk.
- **Your automations run whether or not a vendor's service is up.** Outages at Zapier, Clay, or Apollo don't stop your scripts from processing local data.
- **It's dramatically cheaper.** A Mac Mini costs $500-600 once. The SaaS tools it replaces cost $2,000+/year, every year.

---

## launchd: Your Built-In Task Scheduler

Every Mac has `launchd` running in the background. It's the macOS equivalent of `cron`, but more capable. It can run scripts:

- On a recurring schedule (every hour, every day at 6am)
- At system boot
- When a file changes
- When a network connection comes up

This is how you build GTM automation that survives restarts, runs silently in the background, and never needs a platform.

**How it works:** You write a `.plist` file (XML) that tells launchd what to run and when. You load it, and it runs forever — or until you unload it.

**Example: A daily GTM enrichment job.**

Create a file at `~/Library/LaunchAgents/com.gtm.daily-enrich.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gtm.daily-enrich</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/you/gtm-os/scripts/daily_enrich.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/you/gtm-os/logs/enrich.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/you/gtm-os/logs/enrich-error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

Load it:

```bash
# Load the job (starts running on schedule)
launchctl load ~/Library/LaunchAgents/com.gtm.daily-enrich.plist

# Check that it's loaded
launchctl list | grep gtm

# Run it manually right now (for testing)
launchctl start com.gtm.daily-enrich

# Unload it (stop running)
launchctl unload ~/Library/LaunchAgents/com.gtm.daily-enrich.plist
```

That's it. Every day at 6am, your script runs. Output goes to a log file. Errors go to a separate log. No Docker. No cloud. No monthly bill.

**launchd vs cron:** On macOS, `launchd` is the native scheduler and Apple recommends it over cron. The key advantage: if your Mac is asleep at the scheduled time, launchd runs the job as soon as the machine wakes up. Cron just skips it.

---

## SQLite: Your Local Database

SQLite is the most deployed database engine in the world. It runs on every Mac, every iPhone, every Android device, and most web browsers. And it's perfect for GTM data.

Why SQLite instead of Postgres or MySQL:

- **Zero setup.** It's already on your Mac. No server to install or configure.
- **File-based.** Your database is a single file. Back it up by copying it. Version it with git. Move it to another machine by dragging it.
- **Fast enough.** SQLite handles millions of rows without breaking a sweat. Your contact list, campaign tracking, lead scores, and activity logs will never outgrow it.
- **Your agent speaks it.** Claude Code can query SQLite directly, generate reports, and update records through natural language.

**Setting up a GTM database:**

```sql
-- Create your GTM database
-- Run: sqlite3 ~/gtm-os/data/gtm.db

-- Contacts table
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    company TEXT,
    domain TEXT,
    linkedin_url TEXT,
    lead_score INTEGER DEFAULT 0,
    source TEXT,
    enriched_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Campaigns table
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,  -- 'outbound', 'content', 'event'
    status TEXT DEFAULT 'draft',  -- 'draft', 'active', 'paused', 'completed'
    started_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Activity log
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    campaign_id INTEGER REFERENCES campaigns(id),
    action TEXT NOT NULL,  -- 'email_sent', 'email_opened', 'replied', 'meeting_booked'
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Quick views
CREATE VIEW v_hot_leads AS
SELECT c.*, COUNT(a.id) as activity_count
FROM contacts c
LEFT JOIN activity_log a ON c.id = a.contact_id
WHERE c.lead_score >= 80
GROUP BY c.id
ORDER BY c.lead_score DESC;
```

Now your agent can answer questions like:

```
> How many hot leads do we have this week?
> Show me all contacts from Stripe who haven't been contacted.
> What's the reply rate on the "VP Engineering" campaign?
```

And it queries the database directly. No dashboard. No SaaS login. Just SQL.

---

## File-Based GTM: Markdown + SQLite + Git

The local-first GTM stack is simpler than you think:

```
~/gtm-os/
├── CLAUDE.md              # Agent operating instructions
├── data/
│   └── gtm.db             # SQLite database (contacts, campaigns, logs)
├── demand/
│   ├── icp.md             # Ideal Customer Profile
│   ├── positioning.md     # Positioning + messaging
│   └── competitors.md     # Competitive landscape
├── scripts/
│   ├── daily_enrich.py    # Daily enrichment cron job
│   ├── weekly_report.py   # Weekly pipeline report
│   └── score_leads.py     # Lead scoring logic
├── logs/
│   ├── enrich.log         # Script output logs
│   └── errors.log         # Error logs
├── exports/
│   └── hot_leads.csv      # Exported lists for outbound tools
└── .env                   # API keys (never committed)
```

Everything is version controlled with git. Your ICP evolves over time? `git log demand/icp.md` shows every change. Your lead scoring logic changes? The diff tells you exactly what shifted and when.

Compare this to a SaaS tool where your ICP definition lives in a text field inside a settings page, your scoring rules are buried in a workflow builder, and your campaign history disappears when you cancel your subscription.

---

## The Security Advantage

This matters more than most people realize.

When your prospect list lives in HubSpot, it also lives on HubSpot's servers, their backup systems, their analytics pipeline, and potentially their AI training data. When you use Clay for enrichment, your target accounts pass through their infrastructure. When you use Zapier for automation, your API keys are stored in their vault.

Each vendor is an attack surface. Each integration is a potential leak.

With local-first GTM:

- **Your prospect data stays on your machine.** The only time it leaves is when you make an outbound API call (enrichment, email send). Even then, you control exactly what data goes where.
- **Your API keys are in your local `.env` or system keychain.** Not in three different SaaS platforms' settings pages.
- **There's no admin panel a hacker can log into.** No "forgot password" flow to exploit. No OAuth tokens to steal from a vendor breach.
- **Your database is a file.** Encrypt your disk (FileVault on macOS — turn it on), and your data is encrypted at rest.

[Chapter 04](./04-oauth-cli-apis.md) is the vault those keys live in. [Chapter 24](./24-enrichment-on-the-go.md) is one key called from the repo and from a phone agent, so the enrichment call travels with the work.

This doesn't mean local-first is immune to security issues. Someone with physical access to your machine could still access your data. But the attack surface is orders of magnitude smaller than a stack of 8 SaaS tools.

---

## Mac Mini as Always-On GTM Server

A $500-600 Mac Mini runs 24/7 with:
- 8GB+ RAM (plenty for Python scripts and SQLite)
- launchd running your scheduled jobs
- SQLite storing your GTM data
- Python scripts handling enrichment, scoring, and outbound
- Git syncing your workspace to GitHub for backup

**The cost math:**

| | SaaS Stack | Mac Mini |
|---|---|---|
| CRM enrichment | $100-300/mo | API costs only ($20-50/mo) |
| Automation platform | $50-200/mo | $0 (launchd) |
| Data storage | $50-100/mo | $0 (local disk) |
| Reporting | $50-100/mo | $0 (Python + SQLite) |
| **Total** | **$250-700/mo** | **$20-50/mo** + one-time $600 |
| **Annual** | **$3,000-8,400** | **$240-600** + hardware |

The Mac Mini pays for itself in 1-3 months. After that, your marginal cost is just API calls — which you'd be paying for regardless.

**Setup:**
1. Enable Remote Login (System Settings → General → Sharing → Remote Login). This lets you SSH in from anywhere.
2. Disable sleep (System Settings → Energy → Prevent automatic sleeping).
3. Set up your GTM workspace, scripts, and launchd jobs.
4. Optionally install Tailscale for secure remote access from any network.

---

## What Runs Locally vs. What Needs Cloud

Not everything can be local. Here's the split:

**Runs locally (no internet needed):**
- Database queries and reporting
- Lead scoring and segmentation logic
- Data cleaning and deduplication
- Content drafting and editing (with local Ollama models)
- File processing, CSV manipulation
- Git version control

**Needs internet but processes locally:**
- Enrichment API calls (Apollo, Clearbit) — data comes back to your machine
- Email sends (Instantly, Smartlead, SES API)
- CRM sync (push/pull from HubSpot via API)
- Web scraping and research (Exa, Firecrawl)
- AI inference via API (Claude, GPT) — prompts go out, responses come back

**Genuinely cloud-dependent:**
- Receiving inbound webhooks (your Mac needs a public URL or use a tunnel like ngrok/Cloudflare Tunnel)
- Hosting public-facing landing pages (use Vercel or Cloudflare Pages)
- Sending email at scale (you need a proper email service for deliverability)

The key insight: the thinking and storage happen locally. The cloud is just for sending and receiving.

---

## Local AI: Ollama

One more piece of the local-first stack: running AI models on your machine.

[Ollama](https://ollama.com) lets you run open-source language models locally. No API key. No per-token cost. No data leaving your machine.

```bash
# Install
brew install ollama

# Pull a model
ollama pull qwen2.5:14b

# Use it in scripts
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:14b",
  "prompt": "Score this lead based on the following data...",
  "stream": false
}'
```

**When to use local models vs. API models:**

| Use Local (Ollama) | Use API (Claude, GPT) |
|---|---|
| High-frequency, low-stakes: lead scoring, data classification, email categorization | High-stakes: content creation, prospect research, strategic analysis |
| Cost-sensitive: tasks that run hundreds of times per day | Quality-sensitive: anything customer-facing |
| Privacy-critical: processing sensitive prospect data | Context-heavy: tasks that need a large context window |

You don't have to choose one. The best setup uses both: local models for the high-frequency grunt work, API models for the tasks where quality matters most.

---

## Exercise: Build Your Local GTM Stack

Do this now:

1. **Create your GTM database.** Copy the SQL schema from the SQLite section above and run it:
   ```bash
   sqlite3 ~/gtm-os/data/gtm.db < schema.sql
   ```

2. **Write one launchd plist.** Pick your most common manual task. Write a script that does it, then create a plist to schedule it. Load it and verify it runs.

3. **Check FileVault.** System Settings → Privacy & Security → FileVault. If it's off, turn it on. Your prospect data should be encrypted at rest.

4. **Install Ollama.** Even if you don't use it today, having a local model available changes what's possible. Pull `qwen2.5:14b` and test a simple prompt.

---

## Key Takeaways

- Your Mac already has a task scheduler (launchd), a database (SQLite), a scripting runtime (Python), and version control (git). You're paying SaaS vendors for things your laptop does natively.
- SQLite handles millions of rows, lives in a single file, and your agent can query it directly. No server to manage.
- Local-first is a security advantage. Fewer vendors means fewer breach surfaces. Your data on your encrypted disk is harder to steal than your data on 8 different SaaS platforms.
- A Mac Mini pays for itself in 1-3 months compared to a typical SaaS GTM stack. After that, your ongoing cost is just API calls.
- The cloud is for sending and receiving. The thinking and storage happen on your machine.

---

**Next:** [Chapter 07 - Python for GTM](./07-python-for-gtm.md) — Write enrichment scripts, API calls, and CSV pipelines that power your GTM engine.
