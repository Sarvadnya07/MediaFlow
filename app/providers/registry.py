"""
MediaDock Provider Registry.
Manages provider discovery, priority matching, and capability reporting.
"""
from typing import Dict, List, Optional
from app.providers.base import BaseProvider, ProviderInfo
from app.providers.direct import DirectHttpProvider
from app.providers.ytdlp import YtDlpProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: List[BaseProvider] = []
        # Register standard default providers in priority order
        self.register(DirectHttpProvider())
        self.register(YtDlpProvider())

    def register(self, provider: BaseProvider):
        """Register a provider instance."""
        self._providers.append(provider)

    def get_provider_for_url(self, url: str) -> Optional[BaseProvider]:
        """Find the highest-priority provider matching the given URL."""
        for provider in self._providers:
            if provider.matches_url(url):
                return provider
        return None

    def get_provider_by_id(self, provider_id: str) -> Optional[BaseProvider]:
        """Retrieve a provider by its unique identifier."""
        for provider in self._providers:
            if provider.info.id == provider_id:
                return provider
        return None

    def list_providers(self) -> List[ProviderInfo]:
        """Return information for all registered providers."""
        return [p.info for p in self._providers]

    def check_all_providers(self) -> List[Dict]:
        """Run health and compatibility checks on all providers."""
        results = []
        for p in self._providers:
            results.append(p.check_health())
        return results


# Global singleton instance
provider_registry = ProviderRegistry()
