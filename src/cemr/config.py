"""Scenario configuration: scenarios/defaults.toml deep-merged with a scenario file and CLI overrides."""

import copy
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "scenarios"
DEFAULTS_FILE = SCENARIOS_DIR / "defaults.toml"


def deep_merge(base: dict, override: dict) -> dict:
    """Return a copy of `base` with `override` applied recursively (lists and scalars are replaced)."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def resolve_scenario(name_or_path: str) -> Path:
    """Accept a path, a file name in scenarios/, or a short id such as "c1" (matches c1_*.toml)."""
    path = Path(name_or_path)
    if path.is_file():
        return path
    for candidate in (SCENARIOS_DIR / name_or_path, SCENARIOS_DIR / f"{name_or_path}.toml"):
        if candidate.is_file():
            return candidate
    matches = sorted(SCENARIOS_DIR.glob(f"{name_or_path}_*.toml"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"scenario {name_or_path!r} not found in {SCENARIOS_DIR}")


def load_config(scenario: str | None = None, overrides: dict | None = None) -> dict:
    with DEFAULTS_FILE.open("rb") as fh:
        cfg = tomllib.load(fh)
    if scenario:
        with resolve_scenario(scenario).open("rb") as fh:
            cfg = deep_merge(cfg, tomllib.load(fh))
    if overrides:
        cfg = deep_merge(cfg, overrides)
    return cfg
