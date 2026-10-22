"""
prospeo_enrich.py: call the current Prospeo API from the terminal.

Account check, person search, verified-email enrich, verified-mobile enrich,
and a call-route step. Reads PROSPEO_API_KEY from the environment or a
gitignored .env. Never prints the key.

The endpoints below are the public API (V2), checked against
https://prospeo.io/api-docs. This file does not invent paths.

  GET  https://api.prospeo.io/account-information     free
  POST https://api.prospeo.io/search-person           1 credit if the page has a person
  POST https://api.prospeo.io/enrich-person           used for one record
  POST https://api.prospeo.io/bulk-enrich-person      up to 50 records

Auth header on every call: X-KEY. POST bodies are JSON.

Usage:
  python3 prospeo_enrich.py account
  python3 prospeo_enrich.py search --domain example.com --seniority "C-Suite" --dry-run
  python3 prospeo_enrich.py enrich sample_contacts.csv --mode email --dry-run
  python3 prospeo_enrich.py enrich sample_contacts.csv --mode mobile --limit 5
  python3 prospeo_enrich.py route sample_contacts.csv --dry-run

A live enrich or route spends credits when a row hits. Default --limit is 5.
--dry-run sends nothing. Run account (free) before a live batch.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - import guard for a bare environment
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False


HOST = "https://api.prospeo.io"
BULK_MAX = 50
DEFAULT_LIMIT = 5

# https://prospeo.io/api-docs/enum/seniorities
SENIORITIES = (
    "Founder/Owner",
    "C-Suite",
    "Partner",
    "Vice President",
    "Head",
    "Director",
    "Manager",
    "Senior",
    "Entry",
    "Intern",
)

# Row-level results. The batch continues.
ROW_CODES = {"NO_MATCH", "INVALID_DATAPOINTS"}
# Stop the run. Retrying will not help.
FATAL_CODES = {
    "INVALID_API_KEY",
    "INSUFFICIENT_CREDITS",
    "INVALID_REQUEST",
    "INVALID_FILTERS",
    "PLAN_REQUIRED",
}
# Worth one more try.
RETRY_CODES = {"INTERNAL_ERROR", "SERVICE_TEMPORARILY_UNAVAILABLE"}

MATCH_FIELDS = (
    "first_name",
    "last_name",
    "full_name",
    "linkedin_url",
    "email",
    "company_name",
    "company_website",
    "company_linkedin_url",
    "person_id",
)

CLEARED = "cleared-to-call"
EMAIL_ONLY = "email-only"
PENDING = "pending-checks"
NO_CHANNEL = "no-channel"


class ProspeoError(Exception):
    def __init__(self, message: str, code: str = "", key: str = ""):
        self.code = code
        super().__init__(redact(message, key))


def redact(text: str, key: str) -> str:
    if not text:
        return ""
    out = text
    if key:
        out = out.replace(key, "[redacted]")
    return out


def load_key() -> str:
    """Environment wins, then .env next to this script, then .env in the cwd."""
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    load_dotenv()
    key = (os.environ.get("PROSPEO_API_KEY") or "").strip()
    if not key or key == "your_api_key_here":
        raise ProspeoError(
            "PROSPEO_API_KEY is missing. Copy examples/scripts/.env.example to "
            "examples/scripts/.env and put the key there, or export it in the shell. "
            "Do not paste it into chat."
        )
    return key


def normalize_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    raw = raw.split("/")[0].strip()
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def truthy(value: str | None) -> bool | None:
    if value is None:
        return None
    token = str(value).strip().lower()
    if token in ("",):
        return None
    if token in ("true", "yes", "1", "y"):
        return True
    if token in ("false", "no", "0", "n"):
        return False
    return None


def matchable(row: dict) -> bool:
    """Minimum datapoints from the Enrich Person docs."""
    if (row.get("person_id") or "").strip():
        return True
    if (row.get("linkedin_url") or "").strip():
        return True
    if (row.get("email") or "").strip():
        return True
    has_name = bool((row.get("full_name") or "").strip()) or (
        bool((row.get("first_name") or "").strip()) and bool((row.get("last_name") or "").strip())
    )
    has_company = any((row.get(field) or "").strip() for field in (
        "company_name", "company_website", "company_linkedin_url",
    ))
    return has_name and has_company


def company_name_only(row: dict) -> bool:
    has_name = bool((row.get("full_name") or "").strip()) or (
        bool((row.get("first_name") or "").strip()) and bool((row.get("last_name") or "").strip())
    )
    only_name = bool((row.get("company_name") or "").strip()) and not any(
        (row.get(field) or "").strip() for field in ("company_website", "company_linkedin_url", "person_id", "linkedin_url", "email")
    )
    return has_name and only_name


def build_person_record(row: dict, identifier: str) -> dict:
    record = {"identifier": str(identifier)}
    for field in MATCH_FIELDS:
        value = (row.get(field) or "").strip()
        if not value:
            continue
        if field == "company_website":
            value = normalize_domain(value)
        record[field] = value
    return record


def enrich_body(records: list[dict], mode: str) -> dict:
    if mode == "email":
        flags = {"only_verified_email": True}
    elif mode == "mobile":
        # only_verified_mobile implies enrich_mobile on the API.
        flags = {"only_verified_mobile": True}
    else:
        raise ProspeoError(f"unknown enrich mode: {mode}")
    return {**flags, "data": records}


def build_search_body(domains: list[str], seniorities: list[str] | None,
                      titles: list[str] | None, has_mobile: bool, has_email: bool,
                      page: int) -> dict:
    filters: dict = {
        "company": {
            "websites": {"include": [normalize_domain(d) for d in domains if normalize_domain(d)]}
        }
    }
    if not filters["company"]["websites"]["include"]:
        raise ProspeoError("search needs at least one domain, like example.com")
    if seniorities:
        unknown = [s for s in seniorities if s not in SENIORITIES]
        if unknown:
            raise ProspeoError(
                "seniority must be one of: " + ", ".join(SENIORITIES) + f". Got {unknown}"
            )
        filters["person_seniority"] = {"include": list(seniorities)}
    if titles:
        filters["person_job_title"] = {"include": list(titles), "match_mode": "CONTAINS"}
    contact: dict = {}
    if has_email:
        contact["email"] = ["VERIFIED"]
    if has_mobile:
        contact["mobile"] = ["VERIFIED"]
    if contact:
        if has_email and has_mobile:
            contact["operator"] = "AND"
        filters["person_contact_details"] = contact
    return {"page": page, "filters": filters}


def usable_contact(block: dict | None) -> tuple[str, str]:
    """Return (status, revealed value). Masked or unrevealed values stay blank."""
    if not isinstance(block, dict):
        return "", ""
    status = str(block.get("status") or "")
    revealed = bool(block.get("revealed"))
    raw = ""
    for key in ("email", "mobile_international", "mobile", "mobile_national"):
        candidate = block.get(key)
        if isinstance(candidate, str) and candidate.strip():
            raw = candidate.strip()
            break
    if not revealed or "*" in raw or status != "VERIFIED":
        return status, ""
    return status, raw


def hash_number(number: str) -> str:
    """SHA-256 of the E.164-ish form. The hash is what a do-not-call file stores."""
    cleaned = re.sub(r"[^\d+]", "", number or "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def dnc_file_match(number: str, path: str | None) -> bool | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    digest = hash_number(number)
    hashes = {line.strip().lower() for line in file_path.read_text().splitlines() if line.strip()}
    return digest in hashes


def route_contact(*, email_verified: bool, mobile_number: str, mobile_status: str,
                  phone_type: str | None, dnc_match: bool | None) -> str:
    """
    Order: verified mobile, then phone type, then do-not-call.
    cleared-to-call and email-only are finished routes.
    pending-checks means a verified mobile is in hand and a later check has
    not run. Do not dial that row. The verified email can still be mailed.
    """
    has_mobile = mobile_status == "VERIFIED" and bool(mobile_number)
    phone = (phone_type or "").strip().lower() or None
    if not has_mobile:
        return EMAIL_ONLY if email_verified else NO_CHANNEL
    if phone is None:
        return PENDING
    if phone != "mobile":
        return EMAIL_ONLY if email_verified else NO_CHANNEL
    if dnc_match is None:
        return PENDING
    if dnc_match:
        return EMAIL_ONLY if email_verified else NO_CHANNEL
    return CLEARED


def read_csv(path: str) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def credit_ceiling(mode: str, count: int) -> int:
    # Docs: 1 credit per email found, 10 per mobile found. Ceiling assumes every row hits.
    if mode == "mobile":
        return 10 * count
    return count


class ProspeoClient:
    def __init__(self, api_key: str, session=None, sleep=time.sleep, max_retries: int = 4):
        if requests is None and session is None:
            raise ProspeoError("install requests: pip install requests python-dotenv")
        self.api_key = api_key
        self.session = session if session is not None else requests.Session()
        self.sleep = sleep
        self.max_retries = max_retries

    def _headers(self, method: str) -> dict:
        headers = {"X-KEY": self.api_key}
        if method != "GET":
            headers["Content-Type"] = "application/json"
        return headers

    def _wait_seconds(self, response, attempt: int) -> float:
        headers = {k.lower(): v for k, v in getattr(response, "headers", {}).items()}
        daily_left = headers.get("x-daily-request-left")
        if daily_left is not None and str(daily_left).strip() == "0":
            reset = headers.get("x-daily-reset-seconds", "")
            raise ProspeoError(
                f"daily rate limit reached. reset in {reset} seconds. "
                "https://prospeo.io/api-docs/rate-limits",
                code="RATE_LIMIT",
                key=self.api_key,
            )
        minute_left = headers.get("x-minute-request-left")
        if minute_left is not None and str(minute_left).strip() == "0":
            try:
                return min(float(headers.get("x-minute-reset-seconds") or 5), 60.0)
            except ValueError:
                return 5.0
        return min(2 ** attempt, 30)

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = HOST + path
        last_code = ""
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(method),
                    json=body if method != "GET" else None,
                    timeout=45,
                )
            except Exception as exc:
                raise ProspeoError(str(exc), key=self.api_key) from exc
            if response.status_code == 429:
                self.sleep(self._wait_seconds(response, attempt))
                last_code = "RATE_LIMIT"
                continue
            try:
                data = response.json()
            except ValueError as exc:
                raise ProspeoError(
                    f"{method} {path} returned a non-JSON body (HTTP {response.status_code})",
                    key=self.api_key,
                ) from exc
            if not isinstance(data, dict):
                raise ProspeoError(f"{method} {path} returned an unexpected body", key=self.api_key)
            if data.get("error"):
                code = str(data.get("error_code") or "")
                last_code = code
                if code in RETRY_CODES or "rate limit" in code.lower():
                    self.sleep(min(2 ** attempt, 30))
                    continue
                detail = code or "request failed"
                extra = data.get("filter_error")
                if extra:
                    detail = f"{detail}: {extra}"
                raise ProspeoError(detail, code=code, key=self.api_key)
            return data
        raise ProspeoError(
            f"{method} {path} still failing after {self.max_retries} tries ({last_code})",
            code=last_code or "RATE_LIMIT",
            key=self.api_key,
        )

    def account(self) -> dict:
        payload = self.request("GET", "/account-information")
        return payload.get("response") or {}

    def search_page(self, body: dict) -> dict:
        return self.request("POST", "/search-person", body)

    def enrich_one(self, record: dict, mode: str) -> dict:
        body = enrich_body([record], mode)
        body.pop("data")
        body["data"] = {k: v for k, v in record.items() if k != "identifier"}
        return self.request("POST", "/enrich-person", body)

    def enrich_bulk(self, records: list[dict], mode: str) -> dict:
        if len(records) > BULK_MAX:
            raise ProspeoError(f"bulk enrich accepts {BULK_MAX} records, got {len(records)}")
        return self.request("POST", "/bulk-enrich-person", enrich_body(records, mode))


def remaining_credits(account: dict) -> int | None:
    value = account.get("remaining_credits")
    if isinstance(value, int):
        return value
    return None


def select_rows(rows: list[dict], limit: int) -> tuple[list[tuple[str, dict]], list[str]]:
    chosen = []
    skipped = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        identifier = (row.get("identifier") or "").strip() or f"row-{index}"
        while identifier in seen:
            identifier = f"{identifier}-dup"
        seen.add(identifier)
        if not matchable(row):
            skipped.append(identifier)
            continue
        chosen.append((identifier, row))
        if len(chosen) >= limit:
            break
    return chosen, skipped


def guard_spend(count: int, mode: str, yes: bool, account: dict | None) -> None:
    if count > BULK_MAX and not yes:
        raise ProspeoError(
            f"refusing {count} rows without --yes. The bulk endpoint caps a request at {BULK_MAX}."
        )
    ceiling = credit_ceiling(mode, count)
    print(f"worst case if every row hits: {ceiling} credits. a miss is not charged.")
    if not account:
        return
    left = remaining_credits(account)
    plan = account.get("current_plan") or "unknown plan"
    if left is None:
        print(f"account plan {plan}. remaining credits were not in the response.")
        return
    print(f"account plan {plan}. remaining credits: {left}.")
    if left < ceiling and not yes:
        raise ProspeoError(
            f"remaining credits ({left}) are under the worst case ({ceiling}). "
            "Lower --limit, or pass --yes to run anyway."
        )


def flatten_person(person: dict | None, company: dict | None) -> dict:
    person = person or {}
    company = company or {}
    email_status, email = usable_contact(person.get("email") if isinstance(person.get("email"), dict) else None)
    mobile_block = person.get("mobile") if isinstance(person.get("mobile"), dict) else None
    mobile_status, mobile = usable_contact(mobile_block)
    hq = ""
    phone_hq = company.get("phone_hq") if isinstance(company, dict) else None
    if isinstance(phone_hq, dict):
        hq = str(phone_hq.get("phone_hq") or "")
    return {
        "prospeo_person_id": person.get("person_id") or "",
        "full_name": person.get("full_name") or "",
        "title": person.get("current_job_title") or "",
        "email_status": email_status,
        "email": email,
        "mobile_status": mobile_status,
        "mobile": mobile,
        "company_domain": (company or {}).get("domain") or "",
        "company_phone_hq": hq,
    }


def write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        print("no rows to write")
        return
    fields: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {path}")
    print("full emails and mobiles are in that file only. do not commit it.")


def stdout_line(flat: dict) -> str:
    email_bit = "email revealed" if flat.get("email") else (flat.get("email_status") or "no email")
    if flat.get("mobile"):
        mobile_bit = "mobile revealed"
    else:
        mobile_bit = flat.get("mobile_status") or "no mobile"
    name = flat.get("full_name") or flat.get("prospeo_person_id") or "row"
    return f"  {name}: {email_bit}; {mobile_bit}"


def _print_body(title: str, body: dict) -> None:
    print(title)
    print(json.dumps(body, indent=2))


def cmd_account(client: ProspeoClient) -> int:
    info = client.account()
    kept = {
        "current_plan": info.get("current_plan"),
        "remaining_credits": info.get("remaining_credits"),
        "used_credits": info.get("used_credits"),
        "next_quota_renewal_days": info.get("next_quota_renewal_days"),
        "next_quota_renewal_date": info.get("next_quota_renewal_date"),
    }
    print(json.dumps(kept, indent=2))
    return 0


def cmd_search(args, client: ProspeoClient | None) -> int:
    pages = args.pages
    if pages < 1:
        raise ProspeoError("--pages starts at 1")
    if pages > 1 and not args.yes:
        raise ProspeoError("search defaults to 1 page (25 people, 1 credit if any match). pass --yes for more pages.")
    body = build_search_body(
        args.domain, args.seniority, args.title, args.has_mobile, args.has_email, page=1,
    )
    if args.dry_run:
        _print_body(f"dry-run. POST {HOST}/search-person", body)
        print("search does not reveal email or mobile. revealing is a separate enrich.")
        return 0
    assert client is not None
    found = []
    for page in range(1, pages + 1):
        body["page"] = page
        try:
            payload = client.search_page(body)
        except ProspeoError as exc:
            if exc.code == "NO_RESULTS":
                print(f"page {page}: no results")
                break
            raise
        results = payload.get("results") or []
        pagination = payload.get("pagination") or {}
        print(
            f"page {page}: {len(results)} people. "
            f"free={payload.get('free')}. total_count={pagination.get('total_count')}"
        )
        for item in results:
            flat = flatten_person(item.get("person"), item.get("company"))
            # Search keeps email and mobile masked. Drop anything that slipped through.
            flat["email"] = ""
            flat["mobile"] = ""
            print(stdout_line(flat))
            found.append(flat)
        total_pages = pagination.get("total_page") or page
        if page >= int(total_pages):
            break
    if args.output and found:
        write_csv(args.output, found)
    print("person_id is the handoff to enrich. this command did not reveal contact data.")
    return 0


def _live_client(args) -> tuple[ProspeoClient, dict]:
    key = load_key()
    client = ProspeoClient(key)
    info = client.account()
    return client, info


def cmd_enrich(args, client: ProspeoClient | None, account: dict | None) -> int:
    rows = read_csv(args.csv)
    chosen, skipped = select_rows(rows, args.limit)
    print(f"mode: {args.mode}")
    print(f"rows in file: {len(rows)}. matchable in this batch: {len(chosen)}. skipped: {len(skipped)}")
    if skipped:
        print("skipped (not enough datapoints): " + ", ".join(skipped))
    name_only = [identifier for identifier, row in chosen if company_name_only(row)]
    if name_only:
        print("warning: company name only, match quality drops: " + ", ".join(name_only))
    records = [build_person_record(row, identifier) for identifier, row in chosen]
    if args.dry_run:
        if len(records) == 1:
            one = {k: v for k, v in records[0].items() if k != "identifier"}
            flags = enrich_body(records, args.mode)
            flags.pop("data", None)
            preview = {**flags, "data": one}
            endpoint = "/enrich-person"
        else:
            preview = enrich_body(records, args.mode)
            endpoint = "/bulk-enrich-person"
        _print_body(f"dry-run. POST {HOST}{endpoint}", preview)
        print("no request sent.")
        return 0
    if not records:
        print("nothing to send.")
        return 0
    assert client is not None
    guard_spend(len(records), args.mode, args.yes, account)
    output_rows = []
    chunks = [records[i:i + BULK_MAX] for i in range(0, len(records), BULK_MAX)]
    by_id = {identifier: row for identifier, row in chosen}
    for chunk in chunks:
        if len(chunk) == 1:
            record = chunk[0]
            try:
                payload = client.enrich_one(record, args.mode)
            except ProspeoError as exc:
                if exc.code not in ROW_CODES:
                    raise
                print(f"  {record['identifier']}: {exc.code}")
                output_rows.append({**by_id[record["identifier"]], "error_code": exc.code})
                continue
            flat = flatten_person(payload.get("person"), payload.get("company"))
            flat["free_enrichment"] = payload.get("free_enrichment")
            print(stdout_line(flat))
            output_rows.append({**by_id[record["identifier"]], **flat})
            continue
        payload = client.enrich_bulk(chunk, args.mode)
        print(
            f"bulk: matched={len(payload.get('matched') or [])} "
            f"not_matched={len(payload.get('not_matched') or [])} "
            f"invalid={len(payload.get('invalid_datapoints') or [])} "
            f"total_cost={payload.get('total_cost')}"
        )
        matched = {item.get("identifier"): item for item in (payload.get("matched") or [])}
        missed = set(payload.get("not_matched") or []) | set(payload.get("invalid_datapoints") or [])
        for record in chunk:
            identifier = record["identifier"]
            base = dict(by_id.get(identifier) or {})
            if identifier in matched:
                item = matched[identifier]
                flat = flatten_person(item.get("person"), item.get("company"))
                print(stdout_line(flat))
                output_rows.append({**base, **flat, "total_cost": payload.get("total_cost")})
            else:
                code = "not_matched" if identifier in missed else "missing"
                print(f"  {identifier}: {code}")
                output_rows.append({**base, "error_code": code})
    destination = args.output or str(Path(args.csv).with_suffix(".out.csv"))
    write_csv(destination, output_rows)
    return 0


def checks_for(row: dict, revealed: str, dnc_path: str | None) -> tuple[str | None, bool | None]:
    """
    phone_type and dnc_match on the CSV describe a number already in the mobile
    column. A number Prospeo just revealed still needs those checks, unless a
    local hash file can answer the do-not-call step for that new number.
    """
    if not revealed:
        return None, None
    prior = (row.get("mobile") or "").strip()
    if prior != revealed:
        return None, dnc_file_match(revealed, dnc_path)
    phone = (row.get("phone_type") or "").strip().lower() or None
    dnc = truthy(row.get("dnc_match"))
    if dnc is None:
        dnc = dnc_file_match(revealed, dnc_path)
    return phone, dnc


def cmd_route(args, client: ProspeoClient | None, account: dict | None) -> int:
    rows = read_csv(args.csv)
    eligible = []
    held = []
    for index, row in enumerate(rows, start=1):
        identifier = (row.get("identifier") or "").strip() or f"row-{index}"
        verified = truthy(row.get("email_verified")) is True
        if not verified:
            reason = "email not verified"
            if not matchable(row):
                reason = "email not verified, and not enough datapoints to look up a mobile"
            held.append((identifier, reason))
            continue
        if not matchable(row):
            held.append((identifier, "not enough datapoints for a mobile lookup"))
            continue
        eligible.append((identifier, row))
        if len(eligible) >= args.limit:
            break
    print(f"verified emails eligible for a mobile lookup: {len(eligible)}")
    for identifier, reason in held:
        print(f"  hold {identifier}: {reason}")
    records = [build_person_record(row, identifier) for identifier, row in eligible]
    if args.dry_run:
        if len(records) == 1:
            one = {k: v for k, v in records[0].items() if k != "identifier"}
            preview = {"only_verified_mobile": True, "data": one}
            label = f"dry-run. POST {HOST}/enrich-person with only_verified_mobile"
        else:
            preview = enrich_body(records, "mobile") if records else {"only_verified_mobile": True, "data": []}
            label = f"dry-run. POST {HOST}/bulk-enrich-person with only_verified_mobile"
        _print_body(label, preview)
        print("phone-type and do-not-call run after a mobile comes back. no request sent.")
        return 0
    if not records:
        print("nothing to look up.")
        return 0
    assert client is not None
    guard_spend(len(records), "mobile", args.yes, account)
    singles = {}
    chunks = [records[i:i + BULK_MAX] for i in range(0, len(records), BULK_MAX)]
    for chunk in chunks:
        if len(chunk) == 1:
            record = chunk[0]
            try:
                singles[record["identifier"]] = client.enrich_one(record, "mobile")
            except ProspeoError as exc:
                if exc.code not in ROW_CODES:
                    raise
                singles[record["identifier"]] = {"error_code": exc.code}
            continue
        payload = client.enrich_bulk(chunk, "mobile")
        print(f"bulk total_cost={payload.get('total_cost')}")
        for item in payload.get("matched") or []:
            singles[item.get("identifier")] = item
        for identifier in list(payload.get("not_matched") or []) + list(payload.get("invalid_datapoints") or []):
            singles[identifier] = {"error_code": "not_matched"}

    output_rows = []
    by_id = {identifier: row for identifier, row in eligible}
    for identifier, row in eligible:
        item = singles.get(identifier) or {"error_code": "missing"}
        if item.get("error_code"):
            flat = {}
            mobile = ""
            status = ""
            error_code = item["error_code"]
        else:
            person = item.get("person")
            company = item.get("company")
            flat = flatten_person(person, company)
            mobile = flat.get("mobile") or ""
            status = flat.get("mobile_status") or ""
            error_code = ""
        phone_type, dnc = checks_for(row, mobile, args.dnc_hashes)
        route = route_contact(
            email_verified=True,
            mobile_number=mobile,
            mobile_status=status,
            phone_type=phone_type,
            dnc_match=dnc,
        )
        print(f"  {identifier}: {route}")
        output_rows.append({
            **row,
            **flat,
            "error_code": error_code,
            "phone_type_checked": phone_type or "",
            "dnc_match_checked": "" if dnc is None else str(dnc).lower(),
            "route": route,
        })
    destination = args.output or str(Path(args.csv).with_suffix(".route.out.csv"))
    write_csv(destination, output_rows)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prospeo account, search, enrich, and call routing.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("account", help="free account check: plan and remaining credits")

    search = sub.add_parser("search", help="search people at a domain. does not reveal email or mobile")
    search.add_argument("--domain", action="append", required=True, help="root domain, repeatable")
    search.add_argument("--seniority", action="append", help="enum value, repeatable")
    search.add_argument("--title", action="append", help="job title substring, repeatable")
    search.add_argument("--has-mobile", action="store_true", help="filter to VERIFIED mobile availability")
    search.add_argument("--has-email", action="store_true", help="filter to VERIFIED email availability")
    search.add_argument("--pages", type=int, default=1)
    search.add_argument("--yes", action="store_true", help="allow more than one search page")
    search.add_argument("--dry-run", action="store_true")
    search.add_argument("--output")

    enrich = sub.add_parser("enrich", help="verified email or verified mobile on a CSV")
    enrich.add_argument("csv")
    enrich.add_argument("--mode", choices=("email", "mobile"), required=True)
    enrich.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    enrich.add_argument("--yes", action="store_true")
    enrich.add_argument("--dry-run", action="store_true")
    enrich.add_argument("--output")

    route = sub.add_parser("route", help="verified email, then verified mobile, then call or email")
    route.add_argument("csv")
    route.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    route.add_argument("--yes", action="store_true")
    route.add_argument("--dry-run", action="store_true")
    route.add_argument("--dnc-hashes", help="file of SHA-256 hashes, one per line")
    route.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "account":
        return cmd_account(ProspeoClient(load_key()))
    if args.cmd == "search":
        client = None if args.dry_run else ProspeoClient(load_key())
        return cmd_search(args, client)
    if args.cmd in ("enrich", "route") and args.limit < 1:
        raise ProspeoError("--limit starts at 1")
    if args.cmd == "enrich":
        client, account = (None, None) if args.dry_run else _live_client(args)
        return cmd_enrich(args, client, account)
    if args.cmd == "route":
        client, account = (None, None) if args.dry_run else _live_client(args)
        return cmd_route(args, client, account)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ProspeoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.code:
            print(f"error_code: {exc.code}", file=sys.stderr)
        sys.exit(1)
