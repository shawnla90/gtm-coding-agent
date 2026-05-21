# HubSpot template - landing-page.html

This is the bundled HubL template the starter publishes against by default.
Plain enough to read in 60 seconds, structured enough to be useful.

## How to upload it to your portal

You have two options.

### Option A: HubSpot CLI (recommended)

```bash
# 1. Install the official HubSpot CLI
npm install -g @hubspot/cli

# 2. Authenticate against your portal (browser flow)
hs init

# 3. Upload this template to /landing-engine/ in your portal's Design Manager
cd hubspot-template
hs upload . /landing-engine
```

After upload, `landing-page.html` lives at `/landing-engine/landing-page.html`
in your portal. Set that as `HUBSPOT_TEMPLATE_PATH` in `.env` and the pipeline
will publish against it.

### Option B: Manual paste

1. In HubSpot: Design Manager -> Templates -> File / Folder menu -> New file
2. Type "Coded file", language "HTML & HUBL"
3. Path: `/landing-engine/landing-page.html`
4. Paste the contents of `landing-page.html` from this folder
5. Save, then Publish (top right)
6. Hover over the filename in the file tree -> Copy path. Use that as
   `HUBSPOT_TEMPLATE_PATH` in `.env`

## Replacing it with your own template

Once you've seen the pattern, the smart move is to replace this with one of
your existing landing-page templates. The only contract the pipeline cares
about is:

- The template has a single layout section named `main_content`
- That section contains three custom widgets: `hero`, `body_rich_text`, `cta`
- The widget fields match `module-fields.json` in this folder

If your template uses different module names or different field types, update
`module-fields.json` AND the matching builder in
`scripts/_generate_pages.py::build_layout_sections`. The renaming is the only
required code change.
