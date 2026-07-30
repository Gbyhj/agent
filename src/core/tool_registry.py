"""Bridge: src.core.tool_registry → src.tools.registry"""
import sys, os
_agent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _agent not in sys.path: sys.path.insert(0, _agent)
from agent.src.tools.registry import *
