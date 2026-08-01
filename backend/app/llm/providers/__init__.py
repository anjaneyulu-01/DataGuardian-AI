"""Concrete LLM providers.

One module per vendor. Nothing outside this package may import these
directly — consumers go through `LLMFactory` and program against `BaseLLM`.
"""

from app.llm.providers.grok import GrokProvider

__all__ = ["GrokProvider"]
