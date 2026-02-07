"""通用类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    """买卖方向。"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """订单状态。"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(str, Enum):
    """订单类型。"""
    LIMIT = "limit"
    MARKET = "market"


class BrokerType(str, Enum):
    """券商适配器类型。"""
    EASYTRADER = "easytrader"
    QMT = "qmt"


@dataclass
class OrderResult:
    """下单结果。"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    status: OrderStatus
    message: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Order:
    """订单信息。"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    filled_quantity: int
    avg_price: Decimal
    status: OrderStatus
    order_type: OrderType = OrderType.LIMIT
    created_at: Optional[datetime] = None


@dataclass
class Position:
    """持仓信息。"""
    symbol: str
    name: str
    quantity: int
    available_quantity: int
    cost_price: Decimal
    current_price: Decimal
    market_value: Decimal
    profit: Decimal
    profit_pct: Decimal


@dataclass
class Account:
    """账户信息。"""
    total_asset: Decimal
    available_cash: Decimal
    market_value: Decimal
    frozen_cash: Decimal = Decimal("0")
