"""
enrich-skeleton.py — Contact Enrichment Pipeline

Takes a CSV of contacts (name + company or email) and enriches them
with additional data from enrichment APIs.

A working Prospeo client is prospeo_enrich.py in this directory.
The chapter is chapters/24-enrichment-on-the-go.md.

Usage:
    python enrich-skeleton.py contacts.csv --output enriched_contacts.csv

Requirements:
    pip install requests python-dotenv
"""

import csv
import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 3


def read_contacts(filepath: str) -> list[dict]:
    """
    Read contacts from CSV. Supports multiple input formats:
    - email (enriches from email)
    - first_name + last_name + company (searches for email)
    - linkedin_url (enriches from LinkedIn)
    """
    contacts = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            contacts.append(row)
    print(f"Loaded {len(contacts)} contacts from {filepath}")
    return contacts


def enrich_by_email(email: str) -> dict:
    """
    Enrich a contact by email address.

    Example using Apollo (replace with your provider):
    https://docs.apollo.io/reference/people-enrichment
    """
    if not APOLLO_API_KEY:
        return {"error": "No APOLLO_API_KEY set in .env"}

    # Apollo people enrichment
    # response = requests.post(
    #     "https://api.apollo.io/v1/people/match",
    #     json={"email": email},
    #     headers={"X-Api-Key": APOLLO_API_KEY}
    # )
    # if response.status_code == 200:
    #     person = response.json().get("person", {})
    #     return {
    #         "name": person.get("name"),
    #         "title": person.get("title"),
    #         "company": person.get("organization", {}).get("name"),
    #         "linkedin_url": person.get("linkedin_url"),
    #         "city": person.get("city"),
    #         "seniority": person.get("seniority"),
    #         "departments": person.get("departments"),
    #     }
    # return {"error": f"API returned {response.status_code}"}

    # Placeholder
    return {"email": email, "enriched": False, "note": "Replace with real API call"}


def search_contact(first_name: str, last_name: str, company: str) -> dict:
    """
    Search for a contact by name + company to find their email and details.

    Example using Apollo:
    https://docs.apollo.io/reference/people-search
    """
    if not APOLLO_API_KEY:
        return {"error": "No APOLLO_API_KEY set in .env"}

    # Apollo people search
    # response = requests.post(
    #     "https://api.apollo.io/v1/mixed_people/search",
    #     json={
    #         "person_titles": [],
    #         "q_organization_name": company,
    #         "person_name": f"{first_name} {last_name}",
    #         "page": 1,
    #         "per_page": 1,
    #     },
    #     headers={"X-Api-Key": APOLLO_API_KEY}
    # )
    # if response.status_code == 200:
    #     people = response.json().get("people", [])
    #     if people:
    #         person = people[0]
    #         return {
    #             "email": person.get("email"),
    #             "title": person.get("title"),
    #             "linkedin_url": person.get("linkedin_url"),
    #             "phone": person.get("phone_number"),
    #         }
    # return {"error": "No match found"}

    # Placeholder
    return {
        "name": f"{first_name} {last_name}",
        "company": company,
        "enriched": False,
        "note": "Replace with real API call",
    }


def enrich_contact(contact: dict) -> dict:
    """Route to the right enrichment method based on available data."""
    enrichment = {}

    if contact.get("email"):
        enrichment = enrich_by_email(contact["email"])
    elif contact.get("first_name") and contact.get("company"):
        enrichment = search_contact(
            contact.get("first_name", ""),
            contact.get("last_name", ""),
            contact.get("company", ""),
        )
    else:
        enrichment = {"error": "Need either email or (first_name + company)"}

    return enrichment


def process_contacts(contacts: list[dict]) -> list[dict]:
    """Process each contact through enrichment."""
    results = []
    errors = 0

    for i, contact in enumerate(contacts):
        identifier = contact.get("email") or contact.get("first_name", "unknown")
        print(f"  [{i+1}/{len(contacts)}] Enriching {identifier}...")

        retries = 0
        enrichment = None

        while retries < MAX_RETRIES:
            try:
                enrichment = enrich_contact(contact)
                if "error" not in enrichment or "API" not in enrichment.get(
                    "error", ""
                ):
                    break
            except requests.exceptions.RequestException as e:
                print(f"    Retry {retries+1}: {e}")
            retries += 1
            time.sleep(RATE_LIMIT_DELAY * (retries + 1))  # Backoff

        if enrichment is None:
            enrichment = {"error": f"Failed after {MAX_RETRIES} retries"}
            errors += 1

        results.append(
            {
                **contact,
                **enrichment,
                "enriched_at": datetime.now().isoformat(),
            }
        )

        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nProcessed {len(contacts)} contacts. {errors} errors.")
    return results


def write_results(results: list[dict], output_path: str):
    """Write enriched contacts to CSV."""
    if not results:
        print("No results to write.")
        return

    # Collect all possible fields
    all_fields = set()
    for r in results:
        all_fields.update(r.keys())

    fieldnames = sorted(all_fields)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} enriched contacts to {output_path}")


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python enrich-skeleton.py <contacts.csv> [--output enriched.csv]"
        )
        print("\nExpected CSV columns (any of):")
        print("  - email")
        print("  - first_name, last_name, company")
        print("  - linkedin_url")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "enriched_contacts.csv"

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    print(f"\n--- Contact Enrichment Pipeline ---")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}\n")

    contacts = read_contacts(input_file)
    results = process_contacts(contacts)
    write_results(results, output_file)


if __name__ == "__main__":
    main()
