from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class FinancialDataPoint:
    close: float
    high: float
    low: float
    open: float
    timestamp: datetime
    tradeCount: int
    volume: float
    fivePeriodMovingAverage: float = 0.0
    tenPeriodMovingAverage: float = 0.0
    sixPeriodRsi: float = 0.0


class Cache:
    def __init__(self, ttl_seconds: float) -> None:
        self.value: Optional[Any] = None
        self.last_updated: Optional[datetime] = None
        self.ttl_seconds = ttl_seconds

    def get(self) -> Optional[Any]:
        if self.last_updated and (datetime.now() - self.last_updated).total_seconds() < self.ttl_seconds:
            return self.value
        return None

    def set(self, value: Any) -> None:
        self.value = value
        self.last_updated = datetime.now()