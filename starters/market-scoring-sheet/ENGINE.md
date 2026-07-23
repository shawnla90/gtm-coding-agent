# The sheet engine

`lib/sheet_engine.py` is the developed piece. It is a single, config-driven Python module that turns a pandas DataFrame into an interactive, color-coded Google Sheet. The same engine renders every market sheet in this build, so the styling stays identical and lives in one place. This doc explains how to use it on its own.

## What it produces

A native Google Sheet (not an xlsx), built over gspread and a Google OAuth token:

- a **score gradient** (red to green) on any numeric column, with tunable stops
- **categorical color maps** for tiers, tracks, segments, any enum (exact text match)
- **banding**, a **frozen header row**, **basic filters**, **sized columns**
- a styled **Dashboard** tab (navy title, gray section bands, bold-green KPIs, wrapped bullets)
- **anyone-with-link reader** sharing
- **rebuild in place by sheet id**, so a link you have shared stays valid across re-runs

## The connection it needs

The engine talks to Google as you, over OAuth. It reads a token from `~/.config/gspread/token.json` with the spreadsheets and drive scopes. Create that token once with `setup_oauth.py` (see the README). Without it, the first call fails. This is the part that makes "just paste the prompt into Claude" fall over, and the reason this starter ships a real setup step.

## How to use it

Per the self-contained rule, vendor the engine into your project instead of importing across repos:

```bash
cp lib/sheet_engine.py your_project/lib/sheet_engine.py
```

Then write a thin builder that loads your data, defines a config dict, and calls `build()`. The builder in this starter (`build_sheet.py`) is the reference.

```python
from lib.sheet_engine import build, GREEN, BLUE, YELLOW, GREY

config = {
    "title": "My Market",          # used only when creating a fresh sheet
    "key": existing_sheet_id,      # rebuild IN PLACE by id, or None to create new
    "share": "anyone_reader",      # applied only on a fresh create
    "dashboard": {
        "title": "Dashboard",
        "subtitle": {"title": "...", "sub": "..."},
        "entries": [
            {"kind": "section", "label": "THE MARKET"},
            {"kind": "kpi", "label": "Accounts scored", "value": "250"},
            {"kind": "bullet", "label": "Green 4-5 is the spear list."},
        ],
    },
    "tabs": [{
        "title": "Scored Market",
        "df": dataframe,
        "cols": ["score", "tier", "company", "domain", "fit_reason"],
        "widths": {"company": 160, "fit_reason": 330},
        "numeric": ["score"],
        "cf": [
            {"col": "score", "type": "grad", "stops": (1, 3, 5)},
            {"col": "tier",  "type": "map",  "map": {"A": GREEN, "B": BLUE}},
        ],
    }],
    "raw_tabs": [{"title": "Scoring Model", "values": [["Dimension", "Points"]], "widths": {0: 240}}],
}

url, tabs = build(config)
print(url)
```

## Config reference

| Key | Meaning |
|-----|---------|
| `title` | Sheet name, used only when creating a fresh sheet |
| `key` | An existing sheet id to rebuild in place, or `None` to create new |
| `token` | OAuth token path (default `~/.config/gspread/token.json`) |
| `share` | `"anyone_reader"` to share a freshly created sheet, else omit |
| `dashboard` | `{title, subtitle:{title,sub}, entries:[{kind,label,value}]}` |
| `tabs` | data tabs: `{title, df, cols, widths?, cf?, numeric?}` |
| `raw_tabs` | simple value grids: `{title, values, widths?, header?}` |

Conditional formatting (`cf`) specs:

- `{"col": "score", "type": "grad", "stops": (lo, mid, hi)}` gives a red to yellow to green gradient
- `{"col": "tier", "type": "map", "map": {"A": GREEN, "B": BLUE}}` sets an exact-match color per value

Dashboard entry kinds: `section`, `kpi`, `bullet`, `note`, `blank`.

## Palette

`NAVY GREEN GREEN_DK GREEN_LT BLUE YELLOW AMBER GREY GREY_LT ORANGE RED` (hex strings, no `#`).

## Notes

- The module is pure: no file I/O, no argv. The thin builder owns the data and the paths.
- Pass numeric columns in `numeric` so the gradient and sorting see numbers, not strings.
- A fresh create leaves no stray `Sheet1`; `build()` clears whatever pre-existed after adding the new tabs.
- Large tabs (10k+ rows) render but are heavy. Cap the review tab and keep the full data in your database, then log the cap.
