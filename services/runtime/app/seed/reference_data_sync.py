from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db import get_engine
from app.models.reference_data import AccreditationAttestat, OpsRegistry, ReferenceDictionary, ReferenceDictionaryItem
from app.seed.reference_data_seed import (
    ACCREDITATION_ATTESTATS_SEED,
    MANDATORY_DICTIONARIES,
    MANDATORY_DICTIONARY_ITEMS,
    OPS_REGISTRY_SEED,
)


def sync_reference_data(session: Session) -> dict[str, int]:
    summary = {
        "dictionaries_inserted": 0,
        "dictionaries_updated": 0,
        "dictionary_items_inserted": 0,
        "dictionary_items_updated": 0,
        "ops_registry_inserted": 0,
        "ops_registry_updated": 0,
        "attestats_inserted": 0,
        "attestats_updated": 0,
    }

    dictionary_ids: dict[str, int] = {}
    for entry in MANDATORY_DICTIONARIES:
        dictionary = session.query(ReferenceDictionary).filter(ReferenceDictionary.code == entry["code"]).one_or_none()
        if dictionary is None:
            dictionary = ReferenceDictionary(
                code=entry["code"],
                name=entry["name"],
                description=entry["description"],
                is_active=True,
            )
            session.add(dictionary)
            session.flush()
            summary["dictionaries_inserted"] += 1
        else:
            changed = False
            if dictionary.name != entry["name"]:
                dictionary.name = entry["name"]
                changed = True
            if dictionary.description != entry["description"]:
                dictionary.description = entry["description"]
                changed = True
            if not dictionary.is_active:
                dictionary.is_active = True
                changed = True
            if changed:
                summary["dictionaries_updated"] += 1
        dictionary_ids[entry["code"]] = dictionary.id

    for entry in MANDATORY_DICTIONARY_ITEMS:
        dictionary_id = dictionary_ids[entry["dictionary_code"]]
        item = (
            session.query(ReferenceDictionaryItem)
            .filter(
                ReferenceDictionaryItem.dictionary_id == dictionary_id,
                ReferenceDictionaryItem.code == entry["code"],
            )
            .one_or_none()
        )
        if item is None:
            session.add(
                ReferenceDictionaryItem(
                    dictionary_id=dictionary_id,
                    code=entry["code"],
                    name=entry["name"],
                    sort_order=entry["sort_order"],
                    legal_basis=entry["legal_basis"],
                    is_active=True,
                )
            )
            summary["dictionary_items_inserted"] += 1
            continue
        changed = False
        if item.name != entry["name"]:
            item.name = entry["name"]
            changed = True
        if item.sort_order != entry["sort_order"]:
            item.sort_order = entry["sort_order"]
            changed = True
        if item.legal_basis != entry["legal_basis"]:
            item.legal_basis = entry["legal_basis"]
            changed = True
        if not item.is_active:
            item.is_active = True
            changed = True
        if changed:
            summary["dictionary_items_updated"] += 1

    for entry in OPS_REGISTRY_SEED:
        row = session.query(OpsRegistry).filter(OpsRegistry.ops_code == entry["ops_code"]).one_or_none()
        if row is None:
            session.add(OpsRegistry(**entry, is_active=True))
            summary["ops_registry_inserted"] += 1
            continue
        changed = False
        for field in ("full_name", "bin", "accreditation_attestat_number", "head_name", "city"):
            if getattr(row, field) != entry[field]:
                setattr(row, field, entry[field])
                changed = True
        if not row.is_active:
            row.is_active = True
            changed = True
        if changed:
            summary["ops_registry_updated"] += 1

    for entry in ACCREDITATION_ATTESTATS_SEED:
        row = (
            session.query(AccreditationAttestat)
            .filter(AccreditationAttestat.attestat_number == entry["attestat_number"])
            .one_or_none()
        )
        if row is None:
            session.add(AccreditationAttestat(**entry, is_active=True))
            summary["attestats_inserted"] += 1
            continue
        changed = False
        for field in ("ops_code", "issued_at", "expires_at", "status", "scope_summary"):
            if getattr(row, field) != entry[field]:
                setattr(row, field, entry[field])
                changed = True
        if not row.is_active:
            row.is_active = True
            changed = True
        if changed:
            summary["attestats_updated"] += 1

    session.commit()
    return summary


def main() -> None:
    with Session(get_engine()) as session:
        print(json.dumps(sync_reference_data(session), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
