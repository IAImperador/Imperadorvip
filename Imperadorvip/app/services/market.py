import datetime as dt
from typing import Literal
def is_market_open(now_utc: dt.datetime | None = None) -> bool:
    if now_utc is None:
        now_utc = dt.datetime.utcnow()
    weekday = now_utc.weekday()
    hour = now_utc.hour
    if weekday == 6:
        return hour >= 22
    if weekday in (0,1,2,3):
        return True
    if weekday == 4:
        return hour < 22
    return False
def effective_market(market_flag: Literal["auto","open","otc"]) -> str:
    if market_flag == "open": return "open"
    if market_flag == "otc": return "otc"
    return "open" if is_market_open() else "otc"
