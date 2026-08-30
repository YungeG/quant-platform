"""Online three-session false-breakout rejection rule."""
from __future__ import annotations
from enum import StrEnum
class BreakoutStatus(StrEnum):
 PENDING_D3="PENDING_D3";FALSE_BREAKOUT_ABSOLUTE="FALSE_BREAKOUT_ABSOLUTE";FALSE_BREAKOUT_RELATIVE="FALSE_BREAKOUT_RELATIVE";FALSE_BREAKOUT_BOTH="FALSE_BREAKOUT_BOTH";BREAKOUT_HELD="BREAKOUT_HELD"
def classify_three_day_hold(absolute_closes,relative_closes,absolute_breakout,relative_breakout):
 absolute=list(absolute_closes)[:3];relative=list(relative_closes)[:3]
 if len(absolute)<3 or len(relative)<3:return BreakoutStatus.PENDING_D3
 absolute_failed=any(value<absolute_breakout for value in absolute);relative_failed=any(value<relative_breakout for value in relative)
 if absolute_failed and relative_failed:return BreakoutStatus.FALSE_BREAKOUT_BOTH
 if absolute_failed:return BreakoutStatus.FALSE_BREAKOUT_ABSOLUTE
 if relative_failed:return BreakoutStatus.FALSE_BREAKOUT_RELATIVE
 return BreakoutStatus.BREAKOUT_HELD
