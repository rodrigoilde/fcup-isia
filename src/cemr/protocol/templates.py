"""SPADE templates.

SPADE delivers a message to every behaviour whose template matches it, and a behaviour without a
template matches everything. Each agent therefore has one router (no template) that forwards
messages explicitly; all other behaviours get NEVER so they do not collect copies of every message.
"""

from spade.template import BaseTemplate


class NeverTemplate(BaseTemplate):
    def match(self, message) -> bool:
        return False


NEVER = NeverTemplate()
