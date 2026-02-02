"""
交易接口适配器基类

定义交易接口的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from quant_engine.models.account import Account
from quant_engine.models.order import Order
from quant_engine.models.position import Position


class OrderResult:
    """订单提交结果"""

    def __init__(
        self,
        success: bool,
        broker_order_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.success = success
        self.broker_order_id = broker_order_id
        self.message = message


class Broker(ABC):
    """
    交易接口抽象基类。

    所有交易接口适配器必须实现此接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """接口名称"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass

    @property
    @abstractmethod
    def is_simulation(self) -> bool:
        """是否为模拟交易"""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        连接交易接口。

        Returns:
            是否连接成功

        Raises:
            ConnectionError: 连接失败
            AuthenticationError: 认证失败
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def submit_order(self, order: Order) -> OrderResult:
        """
        提交订单。

        Args:
            order: 订单对象

        Returns:
            订单提交结果

        Raises:
            OrderSubmitError: 订单提交失败
            BrokerNotConnectedError: 未连接
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单。

        Args:
            order_id: 券商订单号

        Returns:
            是否撤销成功

        Raises:
            OrderCancelError: 撤单失败
        """
        pass

    @abstractmethod
    def query_order(self, order_id: str) -> Optional[Order]:
        """
        查询订单状态。

        Args:
            order_id: 券商订单号

        Returns:
            订单对象或 None
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        查询持仓。

        Returns:
            持仓列表
        """
        pass

    @abstractmethod
    def get_account(self) -> Account:
        """
        查询账户信息。

        Returns:
            账户对象
        """
        pass

    def health_check(self) -> bool:
        """
        健康检查。

        Returns:
            是否健康
        """
        return self.is_connected

    def __enter__(self) -> "Broker":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.disconnect()
