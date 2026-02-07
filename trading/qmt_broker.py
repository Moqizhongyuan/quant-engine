"""QMT 券商适配器桩代码，接口预留。"""

from __future__ import annotations

from decimal import Decimal

from common.types import Account, Order, OrderResult, Position
from trading.broker import Broker


class QMTBroker(Broker):
    """QMT 券商适配器（未实现）。"""

    def __init__(self, path: str = "", account_id: str = "") -> None:
        """初始化 QMT 适配器。"""
        self._path = path
        self._account_id = account_id

    def connect(self) -> None:
        """建立 QMT 连接。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def disconnect(self) -> None:
        """断开 QMT 连接。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交买入委托。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交卖出委托。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def cancel_order(self, order_id: str) -> bool:
        """撤销指定订单。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def get_positions(self) -> list[Position]:
        """查询当前持仓。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def get_account(self) -> Account:
        """查询账户资金。"""
        raise NotImplementedError("QMT 适配器尚未实现")

    def get_today_orders(self) -> list[Order]:
        """查询当日委托。"""
        raise NotImplementedError("QMT 适配器尚未实现")
