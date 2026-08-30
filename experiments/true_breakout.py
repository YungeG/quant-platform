"""Online ten-session true-breakout confirmation rule."""
from __future__ import annotations
from enum import StrEnum
class TrueBreakoutStatus(StrEnum):
 PENDING_D10="PENDING_D10";FALSE_BREAKOUT_REJECTED="FALSE_BREAKOUT_REJECTED";UNCONFIRMED_BREAKOUT="UNCONFIRMED_BREAKOUT";TRUE_BREAKOUT_CONFIRMED="TRUE_BREAKOUT_CONFIRMED"
def classify_ten_day_progress(absolute_closes,relative_closes,absolute_breakout,relative_breakout,sector_return10,active_return10):
 absolute=list(absolute_closes)[:10];relative=list(relative_closes)[:10]
 if len(absolute)<10 or len(relative)<10:return TrueBreakoutStatus.PENDING_D10
 if any(value<absolute_breakout for value in absolute) or any(value<relative_breakout for value in relative):return TrueBreakoutStatus.FALSE_BREAKOUT_REJECTED
 if sector_return10>=.07 and active_return10>=.03:return TrueBreakoutStatus.TRUE_BREAKOUT_CONFIRMED
 return TrueBreakoutStatus.UNCONFIRMED_BREAKOUT
