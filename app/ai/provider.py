from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Contract for content-generation providers."""

    @abstractmethod
    def generate_answer(
        self,
        question: str,
        context: list[str],
    ) -> str:
        """Generate an answer using the supplied source context."""

    @abstractmethod
    def generate_application(self, answer: str) -> str:
        """Generate a practical application from an answer."""

    @abstractmethod
    def generate_summary(self, section_content: str) -> str:
        """Generate a summary of a section's content."""

    @abstractmethod
    def generate_heygen_transition(self, subtitle: str) -> str:
        """Generate a spoken transition for a titled section."""
