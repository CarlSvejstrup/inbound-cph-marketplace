#!/usr/bin/env python3
"""By-path loader for the existing skills' deterministic builders.

The optimization loop reuses the skills' ACTUAL builder code as the single source
of truth. It does not copy or fork that code, and it does not modify the skills.
Instead it loads each skill's real module from its file path (importlib) and calls
the same callables the skill's own CLI calls.

Why by-path and not a shared import package: Cowork plugins install as
self-contained single-root directories, and the three skills span two plugin roots
(google-ads-optimization, google-ads-setup). No shared import location exists for the
shipped skills. This loader is repo-local and never ships, so it can point straight
at the skill files. See ../../SPEC.md section 1.1 / 2.

Wrinkle: the RSA builder (fill-sheet.py) imports a sibling module (sheet_layout.py),
so we prepend its directory to sys.path before loading it. The other two builders are
self-contained.

Public API:
  build_search_terms(analysis: dict, out_path: str) -> str
  build_asset_hygiene(analysis: dict, out_path: str) -> str
  build_rsa(ads: dict | list, out_path: str, allow_quality_warnings: bool = False) -> str

Each returns the output path on success. build_rsa raises RsaValidationError if the
ad text fails the skill's own hard length limits or (unless overridden) its quality
guardrails - the SAME gates the skill enforces, because we call the skill's own
validate()/quality_warnings().
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Resolve the repo root from this file: workflows/optimization-loop/lib/builders/load.py
# parents[0]=builders, [1]=lib, [2]=optimization-loop, [3]=workflows, [4]=repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]

_SEARCH_TERMS = _REPO_ROOT / "plugins/google-ads-optimization/skills/search-terms/build-sheet.py"
_ASSET_HYGIENE = _REPO_ROOT / "plugins/google-ads-optimization/skills/annonce-optimering/build-sheet.py"
_RSA_FILL = _REPO_ROOT / "plugins/google-ads-setup/skills/responsive-search-ads/fill-sheet.py"


class RsaValidationError(ValueError):
    """Raised when ad text fails the RSA skill's own length / quality gates."""


def _load_module(path: Path, mod_name: str, add_dir_to_syspath: bool = False):
    """Load a module from an absolute file path without importing the package.

    If add_dir_to_syspath, prepend the module's own directory to sys.path first so
    its sibling imports (e.g. fill-sheet.py -> sheet_layout.py) resolve.
    """
    if not path.exists():
        raise FileNotFoundError(f"builder not found at {path} (repo moved?)")
    if add_dir_to_syspath:
        d = str(path.parent)
        if d not in sys.path:
            sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Modules are loaded lazily and cached so repeated builds in one Workflow run don't
# re-exec the file.
_cache: dict[str, object] = {}


def _st():
    if "st" not in _cache:
        _cache["st"] = _load_module(_SEARCH_TERMS, "_loop_search_terms_builder")
    return _cache["st"]


def _ao():
    if "ao" not in _cache:
        _cache["ao"] = _load_module(_ASSET_HYGIENE, "_loop_asset_hygiene_builder")
    return _cache["ao"]


def _rsa():
    if "rsa" not in _cache:
        # sheet_layout.py is a sibling import inside fill-sheet.py -> need its dir on the path.
        _cache["rsa"] = _load_module(_RSA_FILL, "_loop_rsa_builder", add_dir_to_syspath=True)
    return _cache["rsa"]


def build_search_terms(analysis: dict, out_path: str) -> str:
    """Build the search-terms workbook via the skill's own build(data, out_path)."""
    _st().build(analysis, out_path)
    return out_path


def build_asset_hygiene(analysis: dict, out_path: str) -> str:
    """Build the annonce-optimering workbook via the skill's own build(data, out_path)."""
    _ao().build(analysis, out_path)
    return out_path


def build_rsa(ads, out_path: str, allow_quality_warnings: bool = False) -> str:
    """Build the RSA Editor sheet, enforcing the skill's OWN length + quality gates.

    Replicates the orchestration in the skill's main() (normalise -> hard-limit
    validate -> quality gate -> fill) by calling the skill's own functions, so the
    guarantees are identical. We do not bypass any gate.
    """
    m = _rsa()
    try:
        ad_list = m._ads_list(ads)
    except ValueError as e:
        raise RsaValidationError(f"bad ads.json: {e}") from e

    multi = len(ad_list) > 1
    def label(n):
        return f"RSA {n}, " if multi else ""

    # Hard length limits - never overridable (matches main()).
    hard_errs = []
    for n, ad in enumerate(ad_list, 1):
        hard_errs += [f"{label(n)}{e}" for e in m.validate(ad)]
    if hard_errs:
        raise RsaValidationError("over-length fields: " + "; ".join(hard_errs))

    # Quality guardrails - block by default, overridable (matches main()).
    warns = []
    for n, ad in enumerate(ad_list, 1):
        warns += [f"{label(n)}{w}" for w in m.quality_warnings(ad)]
    if warns and not allow_quality_warnings:
        raise RsaValidationError("quality guardrails failed: " + "; ".join(warns))

    m.fill(ad_list, Path(out_path))
    return out_path
