from __future__ import annotations

from backend.services.download_connectors import DownloadSourceRegistryManager

from .arxiv import ArxivSource
from .europe_pmc import EuropePmcSource, PubMedSource
from .openalex import OpenAlexSource


class PaperSourceFactory:
    def create_registry(self) -> DownloadSourceRegistryManager:
        registry = DownloadSourceRegistryManager()
        registry.register(ArxivSource())
        registry.register(PubMedSource())
        registry.register(EuropePmcSource())
        registry.register(OpenAlexSource())
        return registry

    def create_mapping(self) -> dict[str, object]:
        return self.create_registry().build_mapping()
