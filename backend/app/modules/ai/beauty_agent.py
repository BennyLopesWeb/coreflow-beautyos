"""
Shim de compatibilidade — BeautyAgent migrado para plugin (R2-F4).

Re-exporta ``app.plugins.beauty.agents.beauty_agent``. Preferir import direto
do plugin em código novo.
"""
from app.plugins.beauty.agents.beauty_agent import AgentAnalyzeResult, BeautyAgent

__all__ = ["BeautyAgent", "AgentAnalyzeResult"]
