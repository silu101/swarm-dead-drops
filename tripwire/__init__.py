"""Tripwire: an audit trail and red-flag report for agents that share a folder.

From the Dead Drops project (Apart Swarm Alignment Hackathon, 2026). Standard library only.
"""

from .analyze import Flag, analyze, report_markdown, summarize
from .canary import Canary, leaked_by, make_canaries
from .guard import DEFAULT_PROTECTED, INTEGRITY_MIN_SIGNS, Decision, Guard, inspect_edit, integrity_fires, integrity_signs, is_protected
from .events import Event, EventLog, load, verify
from .workspace import TOOL_SCHEMAS, Workspace, WorkspaceError

__all__ = ["Workspace", "WorkspaceError", "TOOL_SCHEMAS", "EventLog", "Event", "load", "verify",
           "make_canaries", "leaked_by", "Canary", "analyze", "summarize", "report_markdown", "Flag",
           "Guard", "Decision", "DEFAULT_PROTECTED", "inspect_edit", "is_protected",
           "integrity_signs", "integrity_fires", "INTEGRITY_MIN_SIGNS"]
