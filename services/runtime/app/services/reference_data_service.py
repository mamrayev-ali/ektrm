from __future__ import annotations

from fastapi import HTTPException, status

from app.repositories.reference_data_repository import ReferenceDataRepository


class ReferenceDataService:
    def __init__(self, repository: ReferenceDataRepository) -> None:
        self._repository = repository

    def list_dictionaries(self) -> dict[str, object]:
        dictionaries = self._repository.list_dictionaries()
        return {"total": len(dictionaries), "items": dictionaries}

    def list_dictionary_items(self, dictionary_code: str) -> dict[str, object]:
        dictionaries = {item["code"] for item in self._repository.list_dictionaries()}
        if dictionary_code not in dictionaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dictionary '{dictionary_code}' was not found",
            )
        items = self._repository.list_dictionary_items(dictionary_code)
        return {"dictionary_code": dictionary_code, "total": len(items), "items": items}

    def list_ops_registry(self, limit: int, search: str | None) -> dict[str, object]:
        items = self._repository.list_ops_registry(limit=limit, search=search)
        return {"total": len(items), "items": items}

    def list_accreditation_attestats(self, limit: int, search: str | None) -> dict[str, object]:
        items = self._repository.list_accreditation_attestats(limit=limit, search=search)
        return {"total": len(items), "items": items}
