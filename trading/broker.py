"""Broker 抽象基类，定义统一交易接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from types import TracebackType

from common.types import Account, Order, OrderResult, Position


class Broker(ABC):
    """券商适配器统一接口。

    支持 with 语句自动管理连接生命周期。
    """

    @abstractmethod
    def connect(self) -> None:
        """建立与券商的连接。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开与券商的连接。"""

    @abstractmethod
    def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交买入委托。"""

    @abstractmethod
    def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交卖出委托。"""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤销指定订单，返回是否成功。"""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """查询当前持仓列表。"""

    @abstractmethod
    def get_account(self) -> Account:
        """查询账户资金信息。"""

    @abstractmethod
    def get_today_orders(self) -> list[Order]:
        """查询当日委托列表。"""

    def __enter__(self) -> "Broker":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
