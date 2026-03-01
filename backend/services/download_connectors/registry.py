from __future__ import annotations

from dataclasses import dataclass

from .base import DownloadSourceConnector


@dataclass(frozen=True)
class DownloadSourceDescriptor:
    key: str
    label: str


class DownloadSourceRegistryManager:
    def __init__(self):
        self._connectors: dict[str, DownloadSourceConnector] = {}

    def register(self, connector: DownloadSourceConnector) -> None:
        key = str(getattr(connector, "SOURCE_KEY", "") or "").strip()
        if not key:
            raise ValueError("source_key_required")
        self._connectors[key] = connector

    def build_mapping(self) -> dict[str, DownloadSourceConnector]:
        return dict(self._connectors)

    def get(self, source_key: str) -> DownloadSourceConnector | None:
        return self._connectors.get(str(source_key or "").strip())

    def list_descriptors(self) -> list[DownloadSourceDescriptor]:
        return [
            DownloadSourceDescriptor(
                key=key,
                label=str(getattr(connector, "SOURCE_LABEL", "") or key),
            )
            for key, connector in self._connectors.items()
        ]
