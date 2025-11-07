from typing import Literal
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class BotState:
    enabled: bool = False
    mode: Literal["manual","auto"] = "manual"
    market: Literal["open","otc"] = "open"
    last_signal: dict = field(default_factory=dict)
    updated_at: str = datetime.now(timezone.utc).isoformat()

state = BotState()
