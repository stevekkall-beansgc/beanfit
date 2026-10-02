"""Explanatory metadata for legacy catalog ratings; no new scoring policy."""
from __future__ import annotations

from beanfit.catalog.models import CATALOG, USE_CASES


QUALITY_METADATA_AS_OF = "2026-10-02"
QUALITY_CATALOG_REVISION = "42de7df153c5bdfda8199f924ec35ce8cbae9cbd"


def quality_basis(use_case: str | None = None) -> dict:
    """Describe the existing values without inventing their assignment history."""
    if use_case is not None and use_case not in USE_CASES:
        raise ValueError(f"unknown use case: {use_case}")
    result = {
        "schema": 1,
        "scope": "static Mac CLI catalog; not mobile qualification receipts",
        "basis": "legacy_editorial",
        "metadata_as_of": QUALITY_METADATA_AS_OF,
        "catalog_snapshot_revision": QUALITY_CATALOG_REVISION,
        "original_assignment_date": None,
        "assignment_method": "unknown; no historical task set, rubric or reviewer record",
        "empirical_evidence": None,
        "rubric_status": "proposed_not_applied_or_calibrated",
        "intended_audience": "Apple Silicon users shortlisting local models for their own tasks",
        "comparison_basis": "relative illustrative preference within the eight-row catalog",
        "interpretation": "0-10 editorial ranking input; not an accuracy rate or measured quality",
        "uncertainty": "unknown; no calibration, confidence interval or quantified error",
        "documentation": "docs/QUALITY-BASIS.md",
        "inventory": [
            {"runtime_tag": entry.runtime_tag,
             "coding": entry.qual_coding,
             "reasoning": entry.qual_reasoning,
             "chat": entry.qual_chat}
            for entry in CATALOG
        ],
    }
    if use_case is not None:
        result["selected_use_case"] = use_case
        result["selected_catalog_field"] = f"qual_{use_case}"
    return result
