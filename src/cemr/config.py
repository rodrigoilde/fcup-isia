"""Configuração de um cenário: scenarios/defaults.toml, fundido com o ficheiro do cenário e com as
alterações pedidas na linha de comandos."""

import copy
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "scenarios"
DEFAULTS_FILE = SCENARIOS_DIR / "defaults.toml"


def deep_merge(base: dict, override: dict) -> dict:
    """Devolve uma cópia de `base` com `override` aplicado recursivamente (listas e valores são substituídos)."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def resolve_scenario(name_or_path: str) -> Path:
    """Aceita um caminho, um ficheiro de scenarios/ ou um id curto como "c1" (que corresponde a c1_*.toml).

    Raises:
        FileNotFoundError: Se o cenário não existe.
    """
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
    """Lê os parâmetros por omissão e aplica o cenário e as alterações, por esta ordem."""
    with DEFAULTS_FILE.open("rb") as fh:
        cfg = tomllib.load(fh)
    if scenario:
        with resolve_scenario(scenario).open("rb") as fh:
            cfg = deep_merge(cfg, tomllib.load(fh))
    if overrides:
        cfg = deep_merge(cfg, overrides)
    return cfg
