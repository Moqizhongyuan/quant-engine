"""
账户数据模型

定义账户相关的数据结构。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class Account(BaseModel):
    """账户模型"""

    account_id: str = Field(..., description="账户ID")
    account_type: str = Field(default="stock", description="账户类型")

    total_asset: Decimal = Field(default=Decimal("0"), description="总资产")
    cash: Decimal = Field(default=Decimal("0"), description="可用资金")
    frozen_cash: Decimal = Field(default=Decimal("0"), description="冻结资金")
    market_value: Decimal = Field(default=Decimal("0"), description="持仓市值")

    total_profit_loss: Decimal = Field(default=Decimal("0"), description="总盈亏")
    today_profit_loss: Decimal = Field(default=Decimal("0"), description="当日盈亏")

    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @computed_field
    @property
    def available_cash(self) -> Decimal:
        """实际可用资金"""
        return self.cash - self.frozen_cash

    @computed_field
    @property
    def position_ratio(self) -> Decimal:
        """仓位比例"""
        if self.total_asset == 0:
            return Decimal("0")
        return (self.market_value / self.total_asset).quantize(Decimal("0.0001"))


class AccountSnapshot(BaseModel):
    """账户快照（用于记录历史）"""

    id: Optional[int] = Field(None, description="快照ID")
    account_id: str = Field(..., description="账户ID")

    total_asset: Decimal = Field(..., description="总资产")
    cash: Decimal = Field(..., description="可用资金")
    market_value: Decimal = Field(..., description="持仓市值")
    total_profit_loss: Decimal = Field(..., description="总盈亏")

    snapshot_date: datetime = Field(default_factory=datetime.now, description="快照时间")
