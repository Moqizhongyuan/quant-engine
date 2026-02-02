"""
交易信号数据模型

定义交易信号相关的数据结构。
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    """信号方向"""

    BUY = "BUY"
    SELL = "SELL"


class TradingSignal(BaseModel):
    """交易信号模型"""

    id: UUID = Field(default_factory=uuid4, description="信号ID")
    symbol: str = Field(..., description="股票代码", max_length=20)
    name: Optional[str] = Field(None, description="股票名称", max_length=50)

    direction: SignalDirection = Field(..., description="信号方向")
    target_quantity: int = Field(..., description="目标数量", ge=0)
    target_price: Optional[Decimal] = Field(None, description="目标价格")
    target_ratio: Optional[Decimal] = Field(None, description="目标仓位比例")

    source: str = Field(default="manual", description="信号来源")
    strategy_name: Optional[str] = Field(None, description="策略名称")
    reason: Optional[str] = Field(None, description="信号原因")

    executed: bool = Field(default=False, description="是否已执行")
    order_id: Optional[UUID] = Field(None, description="关联订单ID")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    executed_at: Optional[datetime] = Field(None, description="执行时间")

    model_config = {"use_enum_values": True}

    def mark_executed(self, order_id: UUID) -> None:
        """
        标记信号已执行。

        Args:
            order_id: 关联的订单ID
        """
        self.executed = True
        self.order_id = order_id
        self.executed_at = datetime.now()
