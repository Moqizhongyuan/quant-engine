"""
持仓数据模型

定义持仓相关的数据结构。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class Position(BaseModel):
    """持仓模型"""

    id: UUID = Field(default_factory=uuid4, description="持仓ID")
    symbol: str = Field(..., description="股票代码", max_length=20)
    name: Optional[str] = Field(None, description="股票名称", max_length=50)

    quantity: int = Field(default=0, description="持仓数量")
    available_quantity: int = Field(default=0, description="可用数量（T+1）")
    frozen_quantity: int = Field(default=0, description="冻结数量")

    avg_cost: Decimal = Field(default=Decimal("0"), description="平均成本")
    current_price: Decimal = Field(default=Decimal("0"), description="当前价格")

    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @computed_field
    @property
    def market_value(self) -> Decimal:
        """市值"""
        return Decimal(str(self.quantity)) * self.current_price

    @computed_field
    @property
    def cost_value(self) -> Decimal:
        """成本"""
        return Decimal(str(self.quantity)) * self.avg_cost

    @computed_field
    @property
    def profit_loss(self) -> Decimal:
        """盈亏金额"""
        return self.market_value - self.cost_value

    @computed_field
    @property
    def profit_loss_ratio(self) -> Decimal:
        """盈亏比例"""
        if self.cost_value == 0:
            return Decimal("0")
        return (self.profit_loss / self.cost_value).quantize(Decimal("0.0001"))

    def update_price(self, price: Decimal) -> None:
        """
        更新当前价格。

        Args:
            price: 最新价格
        """
        self.current_price = price
        self.updated_at = datetime.now()
