from abc import ABC, abstractmethod
from typing import Any

class ContextProvider(ABC):
    """Abstract base class for dynamic context providers."""
    
    @abstractmethod
    def name(self) -> str:
        """Name of the provider."""
        ...

    @abstractmethod
    def retrieve(self, query: str, config: dict[str, Any]) -> str:
        """Retrieve context based on a query and configuration."""
        ...

class MockVectorStoreProvider(ContextProvider):
    """A mock vector store provider for testing RAG flows."""
    
    def name(self) -> str:
        return "mock_vector_store"

    def retrieve(self, query: str, config: dict[str, Any]) -> str:
        return f"[Mock Context for: {query}]"
