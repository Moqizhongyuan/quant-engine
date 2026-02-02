"""
订单数据模型

定义订单相关的数据结构和枚举类型。
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OrderDirection(str, Enum):
    """订单方向"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型"""

    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"  # 限价单


class OrderStatus(str, Enum):
    """订单状态"""

    PENDING = "PENDING"  # 待提交
    SUBMITTED = "SUBMITTED"  # 已提交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    FILLED = "FILLED"  # 完全成交
    CANCELLED = "CANCELLED"  # 已撤销
    REJECTED = "REJECTED"  # 已拒绝
    FAILED = "FAILED"  # 失败


class Order(BaseModel):
    """订单模型"""

    id: UUID = Field(default_factory=uuid4, description="订单ID")
    symbol: str = Field(..., description="股票代码", max_length=20)
    direction: OrderDirection = Field(..., description="订单方向")
    quantity: int = Field(..., description="委托数量", gt=0)
    price: Optional[Decimal] = Field(None, description="委托价格")
    order_type: OrderType = Field(default=OrderType.LIMIT, description="订单类型")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="订单状态")

    filled_quantity: int = Field(default=0, description="成交数量")
    filled_price: Optional[Decimal] = Field(None, description="成交均价")
    broker_order_id: Optional[str] = Field(None, description="券商订单号")

    signal_id: Optional[UUID] = Field(None, description="关联信号ID")
    error_message: Optional[str] = Field(None, description="错误信息")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    model_config = {"use_enum_values": True}

    @property
    def is_completed(self) -> bool:
        """订单是否已完成（成交、撤销、拒绝或失败）"""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        )

    @property
    def unfilled_quantity(self) -> int:
        """未成交数量"""
        return self.quantity - self.filled_quantity

    def update_status(self, status: OrderStatus, error_message: Optional[str] = None) -> None:
        """
        更新订单状态。

        Args:
            status: 新状态
            error_message: 错误信息（可选）
        """
        self.status = status
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message
