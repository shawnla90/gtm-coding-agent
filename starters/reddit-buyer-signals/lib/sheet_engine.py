#!/usr/bin/env python3
"""proof-sheet engine - parameterized gspread color-coded Google Sheet builder.

Canonical home for the "Duve-style" interactive proof sheet that Shawn ships:
score gradient (red→yellow→green), categorical TEXT_EQ color maps, banding,
frozen headers, basic filters, sized columns, a styled dashboard, and
anyone-with-link sharing - rebuildable IN PLACE by sheet-id so a linked doc
stays valid.

This module is pure (no file I/O, no argv): callers pass pandas DataFrames + a
config dict and get back (url, tab_titles). Projects vendor a copy into
scripts/lib/sheet_engine.py and write a thin per-project builder that loads the
data, defines the config, and calls build(). See SKILL.md for the config schema.
"""
from pathlib import Path

import pandas as pd
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread

DEFAULT_TOKEN = Path.home() / ".config" / "gspread" / "token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# shared palette (hex without #)
NAVY = "1F3A56"
GREEN = "57BB8A"
GREEN_DK = "16653A"
GREEN_LT = "B7E1CD"
BLUE = "C9DAF8"
YELLOW = "FCE8B2"
AMBER = "FFF2CC"
GREY = "EFEFEF"
GREY_LT = "F3F3F3"
ORANGE = "FCE5CD"
RED = "E67C73"


def rgb(h: str) -> dict:
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return None


def creds(token=DEFAULT_TOKEN):
    c = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not c.valid:
        c.refresh(Request())
        Path(token).write_text(c.to_json())
    return c


# ── request builders (semantics proven on the Duve build) ──
def r_header(sid, ncols):
    return [{"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": ncols},
             "cell": {"userEnteredFormat": {"backgroundColor": rgb(NAVY),
                      "textFormat": {"foregroundColor": rgb("FFFFFF"), "bold": True, "fontSize": 10},
                      "verticalAlignment": "MIDDLE"}},
             "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}},
            {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}}]


def r_band(sid, nrows, ncols):
    return {"addBanding": {"bandedRange": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": nrows, "startColumnIndex": 0, "endColumnIndex": ncols},
            "rowProperties": {"headerColor": rgb(NAVY), "firstBandColor": rgb("FFFFFF"), "secondBandColor": rgb("EEF3F8")}}}}


def r_filter(sid, nrows, ncols):
    return {"setBasicFilter": {"filter": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": nrows, "startColumnIndex": 0, "endColumnIndex": ncols}}}}


def r_width(sid, col, px):
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def cf_text(sid, col, nrows, value, color):
    return {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": nrows, "startColumnIndex": col, "endColumnIndex": col + 1}],
            "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": value}]}, "format": {"backgroundColor": rgb(color)}}}, "index": 0}}


def cf_grad(sid, col, nrows, stops=(1, 3, 5)):
    lo, mid, hi = stops
    return {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": nrows, "startColumnIndex": col, "endColumnIndex": col + 1}],
            "gradientRule": {"minpoint": {"color": rgb(RED), "type": "NUMBER", "value": str(lo)},
                             "midpoint": {"color": rgb("FFD666"), "type": "NUMBER", "value": str(mid)},
                             "maxpoint": {"color": rgb(GREEN), "type": "NUMBER", "value": str(hi)}}}, "index": 0}}


def _values(df, cols, numeric):
    out = [cols]
    for _, r in df.iterrows():
        row = []
        for c in cols:
            v = r.get(c, "")
            if c in numeric:
                n = num(v)
                row.append(n if n is not None else "")
            else:
                s = str(v)
                row.append("'" + s if s.startswith("=") else s)
        out.append(row)
    return out


def data_tab(sh, reqs, title, df, cols, widths, cf, numeric):
    ws = sh.add_worksheet(title=title, rows=len(df) + 10, cols=len(cols) + 2)
    ws.append_rows(_values(df, cols, numeric), value_input_option="USER_ENTERED")
    sid, nrows, ncols = ws.id, len(df) + 1, len(cols)
    reqs += r_header(sid, ncols)
    reqs.append(r_band(sid, nrows, ncols))
    reqs.append(r_filter(sid, nrows, ncols))
    for cname, px in widths.items():
        if cname in cols:
            reqs.append(r_width(sid, cols.index(cname), px))
    for spec in cf:
        if spec["col"] not in cols:
            continue
        col = cols.index(spec["col"])
        if spec["type"] == "grad":
            reqs.append(cf_grad(sid, col, nrows, spec.get("stops", (1, 3, 5))))
        else:
            for val, color in spec["map"].items():
                reqs.append(cf_text(sid, col, nrows, val, color))
    return ws


def raw_tab(sh, reqs, title, values, widths=None, header=True):
    """A simple value grid (scoring model, manifest, import log). values = list of rows."""
    ws = sh.add_worksheet(title=title, rows=len(values) + 6, cols=max(len(r) for r in values) + 1)
    ws.append_rows(values, value_input_option="USER_ENTERED")
    if header:
        reqs += r_header(ws.id, len(values[0]))
    for col, px in (widths or {}).items():
        reqs.append(r_width(ws.id, col, px))
    return ws


def dashboard(sh, reqs, title, subtitle, entries):
    """entries: list of {kind, label, value?}. kind ∈ section|kpi|bullet|link|note|blank."""
    rows, sections, kpis, bullets = [], [], [], []
    for e in entries:
        rows.append([e.get("label", ""), e.get("value", "")])
        i = len(rows) - 1
        k = e.get("kind", "kpi")
        if k == "section":
            sections.append(i)
        elif k == "kpi" and str(e.get("value", "")) != "":
            kpis.append(i)
        elif k == "bullet":
            bullets.append(i)

    ws = sh.add_worksheet(title=title, rows=len(rows) + 8, cols=4)
    # title + subtitle occupy the first two rows above the entries
    head = [[subtitle.get("title", ""), ""], [subtitle.get("sub", ""), ""]]
    ws.append_rows(head + rows, value_input_option="USER_ENTERED")
    sid = ws.id
    reqs.append(r_width(sid, 0, 430))
    reqs.append(r_width(sid, 1, 360))
    reqs.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"hideGridlines": True}}, "fields": "gridProperties.hideGridlines"}})
    reqs.append({"mergeCells": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 4}, "mergeType": "MERGE_ALL"}})
    reqs.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 4},
                 "cell": {"userEnteredFormat": {"backgroundColor": rgb(NAVY), "textFormat": {"foregroundColor": rgb("FFFFFF"), "bold": True, "fontSize": 16}, "horizontalAlignment": "LEFT", "padding": {"left": 10}}},
                 "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,padding)"}})
    reqs.append({"mergeCells": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 4}, "mergeType": "MERGE_ALL"}})
    reqs.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 4},
                 "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": rgb("5B6B7B"), "italic": True}}}, "fields": "userEnteredFormat(textFormat)"}})
    off = 2  # entries start after title+subtitle
    for i in sections:
        reqs.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": i + off, "endRowIndex": i + off + 1, "startColumnIndex": 0, "endColumnIndex": 4},
                     "cell": {"userEnteredFormat": {"backgroundColor": rgb("DCE6F1"), "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": rgb(NAVY)}}},
                     "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    for i in kpis:
        reqs.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": i + off, "endRowIndex": i + off + 1, "startColumnIndex": 1, "endColumnIndex": 2},
                     "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12, "foregroundColor": rgb(GREEN_DK)}, "horizontalAlignment": "LEFT"}},
                     "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}})
    for i in bullets:
        reqs.append({"mergeCells": {"range": {"sheetId": sid, "startRowIndex": i + off, "endRowIndex": i + off + 1, "startColumnIndex": 0, "endColumnIndex": 4}, "mergeType": "MERGE_ALL"}})
        reqs.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": i + off, "endRowIndex": i + off + 1, "startColumnIndex": 0, "endColumnIndex": 4},
                     "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "textFormat": {"fontSize": 10}}}, "fields": "userEnteredFormat(wrapStrategy,textFormat)"}})
    return ws


def build(config: dict):
    """Build/rebuild a sheet from a config dict. Returns (url, [tab_titles]).

    config keys:
      title    : sheet name (used only when creating fresh)
      key      : existing sheet id to rebuild IN PLACE, or None to create new
      token    : gspread OAuth token path (default ~/.config/gspread/token.json)
      share    : "anyone_reader" to share a freshly created sheet, else None
      dashboard: {title, subtitle:{title,sub}, entries:[{kind,label,value}]}  (optional)
      tabs     : [{title, df, cols, widths?, cf?, numeric?}]                  data tabs
      raw_tabs : [{title, values, widths?, header?}]                         simple grids
    """
    gc = gspread.authorize(creds(config.get("token", DEFAULT_TOKEN)))
    key = config.get("key")
    sh = gc.open_by_key(key) if key else gc.create(config["title"])
    # Clear pre-existing tabs BEFORE adding new ones so titles don't collide on an
    # in-place rebuild. A throwaway placeholder keeps the sheet non-empty (the API
    # forbids deleting the last sheet); it's dropped once the new tabs exist.
    existing = sh.worksheets()
    placeholder = sh.add_worksheet(title="_rebuilding_", rows=1, cols=1)
    for ws in existing:
        sh.del_worksheet(ws)

    reqs: list = []
    if config.get("dashboard"):
        d = config["dashboard"]
        dashboard(sh, reqs, d["title"], d.get("subtitle", {}), d["entries"])
    for t in config.get("tabs", []):
        data_tab(sh, reqs, t["title"], t["df"], t["cols"], t.get("widths", {}), t.get("cf", []), set(t.get("numeric", [])))
    for rt in config.get("raw_tabs", []):
        raw_tab(sh, reqs, rt["title"], rt["values"], rt.get("widths", {}), rt.get("header", True))

    if reqs:
        sh.batch_update({"requests": reqs})
    sh.del_worksheet(placeholder)
    if not key and config.get("share") == "anyone_reader":
        sh.share(None, perm_type="anyone", role="reader")
    return sh.url, [w.title for w in sh.worksheets()]
