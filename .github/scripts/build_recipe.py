#!/usr/bin/env python3
"""
Parses a GitHub issue body to extract a recipe JSON block,
validates it, and appends it to canonical-recipes.json.

Usage:
    python build_recipe.py --issue-body <file> --output canonical-recipes.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone


REQUIRED_FIELDS = {"fingerprint", "name", "recipe"}


def extract_json_from_issue(body: str) -> dict:
    """Extract the first ```json ... ``` block from an issue body."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, re.DOTALL)
    if not match:
        print("ERROR: No ```json code block found in issue body.", file=sys.stderr)
        sys.exit(1)
    raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in issue body: {e}", file=sys.stderr)
        sys.exit(2)


def validate_recipe(recipe: dict) -> None:
    missing = REQUIRED_FIELDS - recipe.keys()
    if missing:
        print(f"ERROR: Recipe JSON missing required fields: {missing}", file=sys.stderr)
        sys.exit(3)
    if not isinstance(recipe.get("recipe"), dict):
        print("ERROR: 'recipe' field must be an object.", file=sys.stderr)
        sys.exit(3)


def load_canonical(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": 1, "updatedAt": "", "recipes": []}


def check_duplicate(canonical: dict, fingerprint: str) -> None:
    for existing in canonical.get("recipes", []):
        if existing.get("fingerprint") == fingerprint:
            print(
                f"ERROR: Duplicate fingerprint '{fingerprint}' already exists in canonical-recipes.json.",
                file=sys.stderr,
            )
            sys.exit(4)


def save_canonical(path: str, canonical: dict) -> None:
    canonical["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w") as f:
        json.dump(canonical, f, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-body", required=True, help="Path to file containing issue body text")
    parser.add_argument("--output", required=True, help="Path to canonical-recipes.json")
    args = parser.parse_args()

    with open(args.issue_body) as f:
        body = f.read()

    recipe = extract_json_from_issue(body)
    validate_recipe(recipe)

    canonical = load_canonical(args.output)
    check_duplicate(canonical, recipe["fingerprint"])

    canonical["recipes"].append(recipe)
    save_canonical(args.output, canonical)

    print(f"Added recipe: {recipe['name']} ({recipe['fingerprint']})")


if __name__ == "__main__":
    main()
