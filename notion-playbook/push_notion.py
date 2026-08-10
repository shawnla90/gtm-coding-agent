#!/usr/bin/env python3
"""Markdown -> Notion page converter. The shared engine every project pusher imports.

Restored 2026-07-24: this file had gone missing from notion-playbook/ (only a stale .pyc was
left), which broke every `import push_notion` in the client pushers. Restored from an identical
project copy, generalized (--file / --title instead of hardcoded constants), and extended with
markdown TABLE support and mermaid code blocks.

Reads the integration token from ~/.env.notion, converts markdown to Notion blocks (headings,
code, tables, COLORED callouts, to-do checkboxes, bookmark cards, external images, uploaded
images, columns, bullets, dividers, inline bold/code/links), and creates or rebuilds the page.
Prints the URL.

Markdown conventions beyond standard:
  | a | b |                      -> table (a leading header row + |---| separator)
  > 💸 text                      -> callout, color inferred from the leading emoji
  - [ ] text / - [x]             -> to-do checkbox (unchecked / checked)
  ::: bookmark <url>             -> bookmark card
  ::: image <url> | caption      -> external image (GIF/PNG) with optional caption
  ::: image_upload <path> | cap  -> upload a local file, embed it (optional caption)
  ::: columns / ::: column / ::: -> column layout

Usage:
  python3 push_notion.py --file doc.md --title "Title"    # create the page
  python3 push_notion.py --file doc.md --parent <id>      # override parent page id
  python3 push_notion.py --file doc.md --inplace <id>     # rebuild in place (URL preserved)
  python3 push_notion.py --file doc.md --replace <id>     # create new page, archive old one
  python3 push_notion.py --file doc.md --update <id>      # append blocks to an existing page
"""
from __future__ import annotations
import json, mimetypes, re, sys, urllib.request, urllib.error
from pathlib import Path

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_PARENT = "37c1fb92-bcd7-811d-beeb-fa05823ff1ca"  # "Start Here"
HERE = Path(__file__).resolve().parent
MD = HERE / "playbook.md"          # default only; override with --file
TITLE = "Untitled"                 # default only; override with --title

EMOJI_COLOR = {
    "💸": "green_background", "⚡": "blue_background", "🤖": "purple_background",
    "🔥": "orange_background", "✅": "green_background", "📦": "purple_background",
    "🛠️": "gray_background", "🚀": "orange_background", "⏱️": "blue_background",
    "🎯": "pink_background", "💡": "gray_background", "📈": "green_background",
    "🟧": "orange_background", "🔴": "red_background", "🟢": "green_background",
    "⚠️": "red_background", "🧭": "blue_background", "🔍": "gray_background",
}
KNOWN_EMOJI = list(EMOJI_COLOR.keys())
# Notion renders a code block whose language is "mermaid" as a live diagram.
CODE_LANGS = {"bash": "bash", "sh": "shell", "shell": "shell", "python": "python",
              "py": "python", "json": "json", "js": "javascript", "sql": "sql",
              "yaml": "yaml", "yml": "yaml", "mermaid": "mermaid", "": "plain text"}


def load_token() -> str:
    for line in (Path.home() / ".env.notion").read_text().splitlines():
        line = line.strip()
        if line.startswith("NOTION_API_TOKEN"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("NOTION_API_TOKEN not found in ~/.env.notion")


TOKEN = load_token()


def _headers():
    return {"Authorization": f"Bearer {TOKEN}", "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"}


def _req(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Notion API {method} {path} -> {e.code}\n{e.read().decode()}")


def upload_file(path: Path) -> str:
    """Two-step Notion file upload; returns the file_upload id to attach to a block."""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    created = _req("POST", "/file_uploads", {"filename": path.name, "content_type": mime})
    fid, send_url = created["id"], created["upload_url"]
    boundary = "----notionuploadboundary7e3f2a"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n").encode()
    body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(send_url, data=body, method="POST", headers={
        "Authorization": f"Bearer {TOKEN}", "Notion-Version": NOTION_VERSION,
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req) as r:
            r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"file upload send -> {e.code}\n{e.read().decode()}")
    print("  uploaded", path.name, "->", fid)
    return fid


# ---- inline markdown -> rich_text ----
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")
# Notion rejects any single rich_text content longer than this.
MAX_RT = 1900


def _rt(content: str, bold=False, code=False, link=None) -> dict:
    rt = {"type": "text", "text": {"content": content[:MAX_RT]}}
    if link:
        rt["text"]["link"] = {"url": link}
    ann = {}
    if bold:
        ann["bold"] = True
    if code:
        ann["code"] = True
    if ann:
        rt["annotations"] = ann
    return rt


def inline(text: str) -> list:
    out, pos = [], 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            out.append(_rt(text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append(_rt(tok[2:-2], bold=True))
        elif tok.startswith("`"):
            out.append(_rt(tok[1:-1], code=True))
        else:
            lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok)
            out.append(_rt(lm.group(1), link=lm.group(2)))
        pos = m.end()
    if pos < len(text):
        out.append(_rt(text[pos:]))
    return out or [_rt("")]


def _hdr(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": inline(text)}}


def _image_block(img_data: dict, caption: str) -> dict:
    if caption.strip():
        img_data["caption"] = inline(caption.strip())
    return {"object": "block", "type": "image", "image": img_data}


# ---- tables ----
def _split_row(line: str) -> list[str]:
    """Split a markdown table row into cells, dropping the outer pipes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_table_sep(line: str) -> bool:
    """The |---|:--:| separator line directly under a table header."""
    s = line.strip()
    if not s.startswith("|"):
        return False
    return bool(re.fullmatch(r"\|[\s:|-]+\|?", s)) and "-" in s


def _table_block(rows: list[list[str]]) -> dict:
    width = max(len(r) for r in rows)
    children = []
    for r in rows:
        cells = [inline(c) for c in r] + [[_rt("")]] * (width - len(r))
        children.append({"object": "block", "type": "table_row", "table_row": {"cells": cells}})
    return {"object": "block", "type": "table", "table": {
        "table_width": width, "has_column_header": True,
        "has_row_header": False, "children": children}}


def md_to_blocks(md: str) -> list:
    blocks, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip().lower()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            blocks.append({"object": "block", "type": "code", "code": {
                "rich_text": [_rt("\n".join(buf))], "language": CODE_LANGS.get(lang, "plain text")}})
            continue
        s = line.strip()
        if not s:
            i += 1; continue

        # table: a header row, a |---| separator, then body rows
        if s.startswith("|") and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            rows = [_split_row(s)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i])); i += 1
            blocks.append(_table_block(rows))
            continue

        if s == "::: columns":
            i += 1
            cols_raw, cur = [], None
            while i < len(lines) and lines[i].strip() != ":::":
                ls = lines[i].strip()
                if ls == "::: column":
                    cur = []; cols_raw.append(cur)
                elif cur is not None:
                    cur.append(lines[i])
                i += 1
            i += 1  # skip closing :::
            cols = [{"type": "column", "column": {"children": md_to_blocks("\n".join(cl))}}
                    for cl in cols_raw if cl]
            blocks.append({"object": "block", "type": "column_list",
                           "column_list": {"children": cols}})
            continue
        todo = re.match(r"^- \[([ xX])\]\s+(.*)$", s)
        if s == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif s.startswith("::: bookmark "):
            blocks.append({"object": "block", "type": "bookmark",
                           "bookmark": {"url": s[len("::: bookmark "):].strip()}})
        elif s.startswith("::: image_upload "):
            p, _, cap = s[len("::: image_upload "):].partition("|")
            fid = upload_file(Path(p.strip()).expanduser())
            blocks.append(_image_block({"type": "file_upload", "file_upload": {"id": fid}}, cap))
        elif s.startswith("::: image "):
            u, _, cap = s[len("::: image "):].partition("|")
            blocks.append(_image_block({"type": "external", "external": {"url": u.strip()}}, cap))
        elif s.startswith("#### "):
            blocks.append(_hdr(3, s[5:]))
        elif s.startswith("### "):
            blocks.append(_hdr(3, s[4:]))
        elif s.startswith("## "):
            blocks.append(_hdr(2, s[3:]))
        elif s.startswith("# "):
            blocks.append(_hdr(1, s[2:]))
        elif s.startswith("> "):
            content, emoji, color = s[2:], "💡", "gray_background"
            for e in KNOWN_EMOJI:
                if content.startswith(e):
                    emoji, color, content = e, EMOJI_COLOR[e], content[len(e):].lstrip()
                    break
            blocks.append({"object": "block", "type": "callout", "callout": {
                "rich_text": inline(content), "icon": {"emoji": emoji}, "color": color}})
        elif todo:
            blocks.append({"object": "block", "type": "to_do", "to_do": {
                "rich_text": inline(todo.group(2)), "checked": todo.group(1) in ("x", "X")}})
        elif re.match(r"^[-*] ", s):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": inline(s[2:])}})
        elif re.match(r"^\d+\. ", s):
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": inline(re.sub(r"^\d+\. ", "", s))}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": inline(s)}})
        i += 1
    return blocks


def chunk(seq, n):
    for j in range(0, len(seq), n):
        yield seq[j:j + n]


def publish(md_path: Path, title: str, parent: str = DEFAULT_PARENT,
            inplace_id: str | None = None, update_id: str | None = None,
            replace_id: str | None = None, icon: str = "🛠️") -> str | None:
    """Convert md_path and create or rebuild the page. Returns the page URL when it creates one."""
    blocks = md_to_blocks(md_path.read_text())
    print(f"parsed {len(blocks)} blocks from {md_path.name}")

    if update_id:
        for batch in chunk(blocks, 100):
            _req("PATCH", f"/blocks/{update_id}/children", {"children": batch})
        print(f"appended {len(blocks)} blocks to {update_id}")
        return None

    if inplace_id:
        # delete existing children, re-append new ones — keeps the page id + published URL
        existing, cur = [], None
        while True:
            q = f"/blocks/{inplace_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else "")
            d = _req("GET", q)
            existing += d["results"]
            if not d.get("has_more"):
                break
            cur = d["next_cursor"]
        for k in existing:
            _req("DELETE", f"/blocks/{k['id']}")
        print(f"deleted {len(existing)} existing top-level blocks")
        for batch in chunk(blocks, 100):
            _req("PATCH", f"/blocks/{inplace_id}/children", {"children": batch})
        print(f"appended {len(blocks)} blocks in place to {inplace_id} (URL preserved)")
        return None

    first, rest = blocks[:100], blocks[100:]
    page = _req("POST", "/pages", {
        "parent": {"page_id": parent},
        "icon": {"emoji": icon},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": first,
    })
    pid = page["id"]
    for batch in chunk(rest, 100):
        _req("PATCH", f"/blocks/{pid}/children", {"children": batch})
    if replace_id:
        _req("PATCH", f"/pages/{replace_id}", {"archived": True})
        print("archived old page", replace_id)
    print("PAGE_ID:", pid)
    print("URL:", page.get("url"))
    return page.get("url")


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    md_path = Path(opt("--file", str(MD))).expanduser()
    publish(
        md_path=md_path,
        title=opt("--title", TITLE),
        parent=opt("--parent", DEFAULT_PARENT),
        inplace_id=opt("--inplace"),
        update_id=opt("--update"),
        replace_id=opt("--replace"),
    )


if __name__ == "__main__":
    main()
