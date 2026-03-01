from __future__ import annotations

from backend.services.download_connectors import DownloadSourceRegistryManager

from .google_patents import GooglePatentsSource
from .uspto import UsptoSource


class PatentSourceFactory:
    def create_registry(self) -> DownloadSourceRegistryManager:
        registry = DownloadSourceRegistryManager()
        google_source = GooglePatentsSource()
        registry.register(google_source)
        registry.register(UsptoSource(google_source))
        return registry

    def create_mapping(self) -> dict[str, object]:
        return self.create_registry().build_mapping()
