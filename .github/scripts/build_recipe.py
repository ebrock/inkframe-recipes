#!/usr/bin/env python3
"""
Parses, validates, and appends recipe submissions to canonical-recipes.json.

Subcommands:
  add       --issue-body <file> --output <file>   Parse issue body and append to manifest
  validate  --issue-body <file>                   Validate schema only (no output written)
  lint      <manifest>                            Validate all entries in a manifest file
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone


REQUIRED_FIELDS = {"name", "recipe"}

VALID_TOP_LEVEL_FIELDS = {"name", "recipe", "source", "sensor"}

VALID_SENSORS = {"X-Trans II", "X-Trans III", "X-Trans IV", "X-Trans V", "GFX", "Bayer"}

VALID_RECIPE_FIELDS = {
    "filmSimulation", "dynamicRange", "developmentDynamicRange",
    "highlightTone", "shadowTone", "color", "noiseReduction",
    "sharpness", "clarity", "grainEffect", "grainSize",
    "colorChromeEffect", "colorChromeFXBlue", "whiteBalance",
    "whiteBalanceFineTune", "colorTemperature",
}

VALID_FILM_SIMULATIONS = {
    "Provia", "Velvia", "Astia Soft", "Classic Chrome", "Classic Neg",
    "Nostalgic Neg", "Eterna", "Eterna Bleach Bypass", "Reala Ace",
    "Acros", "Acros+R", "Acros+G", "Acros+Ye", "Pro Neg Hi", "Pro Neg Std", "Sepia",
}

VALID_DYNAMIC_RANGE = {"Auto", "Standard"}
VALID_GRAIN_EFFECT = {"Off", "Weak", "Strong"}
VALID_GRAIN_SIZE = {"Small", "Large"}
VALID_CCE = {"Off", "Weak", "Strong"}
VALID_WHITE_BALANCE = {
    "Auto", "Daylight", "Shade", "Fluorescent", "Incandescent", "Underwater", "Kelvin",
}

NUMERIC_RECIPE_FIELDS = {
    "highlightTone", "shadowTone", "color", "noiseReduction",
    "sharpness", "clarity", "colorTemperature",
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def collect_errors(recipe: dict) -> list[str]:
    errors = []

    missing = REQUIRED_FIELDS - recipe.keys()
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")

    unknown = recipe.keys() - VALID_TOP_LEVEL_FIELDS
    if unknown:
        errors.append(f"unknown top-level fields: {sorted(unknown)} (hint: 'fingerprint' was removed from the schema)")

    if "sensor" in recipe and recipe["sensor"] not in VALID_SENSORS:
        errors.append(
            f"invalid sensor '{recipe['sensor']}' — must be one of: {', '.join(sorted(VALID_SENSORS))}"
        )

    settings = recipe.get("recipe")
    if settings is not None:
        if not isinstance(settings, dict):
            errors.append("'recipe' must be an object")
            return errors

        unknown_fields = settings.keys() - VALID_RECIPE_FIELDS
        if unknown_fields:
            errors.append(f"unknown recipe fields: {sorted(unknown_fields)}")

        enum_checks = [
            ("filmSimulation", VALID_FILM_SIMULATIONS),
            ("dynamicRange", VALID_DYNAMIC_RANGE),
            ("grainEffect", VALID_GRAIN_EFFECT),
            ("grainSize", VALID_GRAIN_SIZE),
            ("colorChromeEffect", VALID_CCE),
            ("colorChromeFXBlue", VALID_CCE),
            ("whiteBalance", VALID_WHITE_BALANCE),
        ]
        for field, valid_values in enum_checks:
            if field in settings and settings[field] not in valid_values:
                errors.append(
                    f"invalid {field} '{settings[field]}' — must be one of: {', '.join(sorted(valid_values))}"
                )

    return errors


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize_numeric(value: str) -> str:
    v = value.strip()
    try:
        if float(v) > 0:
            return f"+{v}"
    except ValueError:
        pass
    return v


def _normalize_wb_fine_tune(value: str) -> str:
    parts = [p.strip() for p in value.split(",")]
    normalized = []
    for part in parts:
        tokens = part.split()
        if len(tokens) == 2:
            label, num = tokens
            try:
                if float(num) > 0:
                    num = f"+{num}"
            except ValueError:
                pass
            normalized.append(f"{label} {num}")
        else:
            normalized.append(part)
    return ", ".join(normalized)


def normalize_recipe(recipe: dict) -> dict:
    settings = recipe.get("recipe", {})
    for field in NUMERIC_RECIPE_FIELDS:
        if field in settings and isinstance(settings[field], str):
            settings[field] = _normalize_numeric(settings[field])
    if "whiteBalanceFineTune" in settings:
        settings["whiteBalanceFineTune"] = _normalize_wb_fine_tune(settings["whiteBalanceFineTune"])
    return recipe


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def extract_json_from_issue(body: str) -> dict | None:
    """Return parsed JSON from the first ```json block, or None if not found."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in issue body: {e}", file=sys.stderr)
        sys.exit(2)


def load_canonical(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": 1, "updatedAt": "", "recipes": []}


def save_canonical(path: str, canonical: dict) -> None:
    canonical["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w") as f:
        json.dump(canonical, f, indent=2)
        f.write("\n")


def check_duplicate_name(canonical: dict, name: str) -> None:
    for existing in canonical.get("recipes", []):
        if existing.get("name") == name:
            print(f"ERROR: recipe named '{name}' already exists in canonical-recipes.json.", file=sys.stderr)
            sys.exit(4)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_add(args):
    with open(args.issue_body) as f:
        body = f.read()

    recipe = extract_json_from_issue(body)
    if recipe is None:
        print("ERROR: no ```json code block found in issue body.", file=sys.stderr)
        sys.exit(1)

    errors = collect_errors(recipe)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)

    canonical = load_canonical(args.output)
    check_duplicate_name(canonical, recipe["name"])

    recipe = normalize_recipe(recipe)
    canonical["recipes"].append(recipe)
    save_canonical(args.output, canonical)
    print(f"Added recipe: {recipe['name']}")


def cmd_validate(args):
    """Validate a recipe JSON block from an issue body. Exit 0 if valid or no JSON found."""
    with open(args.issue_body) as f:
        body = f.read()

    recipe = extract_json_from_issue(body)
    if recipe is None:
        sys.exit(0)  # not a recipe issue — skip silently

    errors = collect_errors(recipe)
    if errors:
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

    print(f"Recipe '{recipe.get('name', '')}' passed schema validation.")


def cmd_lint(args):
    """Validate every entry in a manifest file."""
    canonical = load_canonical(args.manifest)
    recipes = canonical.get("recipes", [])
    failed = 0
    for recipe in recipes:
        errors = collect_errors(recipe)
        if errors:
            failed += 1
            name = recipe.get("name", "<unnamed>")
            for e in errors:
                print(f"ERROR [{name}]: {e}", file=sys.stderr)
    if failed:
        sys.exit(3)
    print(f"OK: all {len(recipes)} recipes are valid.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Parse issue body and append recipe to manifest")
    p_add.add_argument("--issue-body", required=True)
    p_add.add_argument("--output", required=True)

    p_val = sub.add_parser("validate", help="Validate recipe schema from an issue body")
    p_val.add_argument("--issue-body", required=True)

    p_lint = sub.add_parser("lint", help="Validate all recipes in a manifest")
    p_lint.add_argument("manifest")

    args = parser.parse_args()
    {"add": cmd_add, "validate": cmd_validate, "lint": cmd_lint}[args.command](args)


if __name__ == "__main__":
    main()
