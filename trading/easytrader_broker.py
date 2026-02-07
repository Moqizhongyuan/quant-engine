"""EasyTrader 券商适配器实现。"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from common.exceptions import BrokerConnectionError, OrderCancelError, OrderSubmitError
from common.types import (
    Account,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from trading.broker import Broker

logger = logging.getLogger(__name__)

# easytrader 订单状态到统一状态的映射
_STATUS_MAP: dict[str, OrderStatus] = {
    "已报": OrderStatus.SUBMITTED,
    "已成": OrderStatus.FILLED,
    "部成": OrderStatus.PARTIAL_FILLED,
    "已撤": OrderStatus.CANCELLED,
    "废单": OrderStatus.REJECTED,
    "未报": OrderStatus.PENDING,
}


def _to_decimal(value: object) -> Decimal:
    """安全转换为 Decimal。"""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


class EasyTraderBroker(Broker):
    """基于 easytrader 库的券商适配器。"""

    def __init__(self, broker_name: str, account: str, password: str, exe_path: str = "") -> None:
        """初始化 EasyTrader 适配器。"""
        self._broker_name = broker_name
        self._account = account
        self._password = password
        self._exe_path = exe_path
        self._client = None

    def connect(self) -> None:
        """连接到券商客户端。"""
        try:
            import easytrader

            self._client = easytrader.use(self._broker_name)
            connect_kwargs: dict = {}
            if self._exe_path:
                connect_kwargs["exe_path"] = self._exe_path
            self._client.prepare(
                user=self._account,
                password=self._password,
                **connect_kwargs,
            )
            logger.info("已连接到券商: %s", self._broker_name)
        except Exception as e:
            raise BrokerConnectionError(f"连接券商失败: {e}") from e

    def disconnect(self) -> None:
        """断开券商连接。"""
        self._client = None
        logger.info("已断开券商连接")

    def _ensure_connected(self) -> None:
        """确保已建立连接。"""
        if self._client is None:
            raise BrokerConnectionError("未连接到券商，请先调用 connect()")

    def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交买入委托。"""
        self._ensure_connected()
        try:
            result = self._client.buy(symbol, price=float(price), amount=quantity)
            order_id = str(result.get("entrust_no", ""))
            logger.info("买入委托已提交: symbol=%s qty=%d price=%s order_id=%s",
                        symbol, quantity, price, order_id)
            return OrderResult(
                order_id=order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                price=price,
                status=OrderStatus.SUBMITTED,
            )
        except Exception as e:
            raise OrderSubmitError(f"买入委托失败: {e}") from e

    def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """提交卖出委托。"""
        self._ensure_connected()
        try:
            result = self._client.sell(symbol, price=float(price), amount=quantity)
            order_id = str(result.get("entrust_no", ""))
            logger.info("卖出委托已提交: symbol=%s qty=%d price=%s order_id=%s",
                        symbol, quantity, price, order_id)
            return OrderResult(
                order_id=order_id,
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                price=price,
                status=OrderStatus.SUBMITTED,
            )
        except Exception as e:
            raise OrderSubmitError(f"卖出委托失败: {e}") from e

    def cancel_order(self, order_id: str) -> bool:
        """撤销指定订单。"""
        self._ensure_connected()
        try:
            self._client.cancel_entrust(order_id)
            logger.info("撤单成功: order_id=%s", order_id)
            return True
        except Exception as e:
            raise OrderCancelError(f"撤单失败: {e}") from e

    def get_positions(self) -> list[Position]:
        """查询当前持仓。"""
        self._ensure_connected()
        raw_positions = self._client.position
        positions: list[Position] = []
        for p in raw_positions:
            positions.append(Position(
                symbol=str(p.get("证券代码", "")),
                name=str(p.get("证券名称", "")),
                quantity=int(p.get("股票余额", 0)),
                available_quantity=int(p.get("可用余额", 0)),
                cost_price=_to_decimal(p.get("成本价", 0)),
                current_price=_to_decimal(p.get("市价", 0)),
                market_value=_to_decimal(p.get("市值", 0)),
                profit=_to_decimal(p.get("盈亏", 0)),
                profit_pct=_to_decimal(p.get("盈亏比例(%)", 0)),
            ))
        return positions

    def get_account(self) -> Account:
        """查询账户资金。"""
        self._ensure_connected()
        raw = self._client.balance
        return Account(
            total_asset=_to_decimal(raw.get("总资产", 0)),
            available_cash=_to_decimal(raw.get("可用金额", 0)),
            market_value=_to_decimal(raw.get("股票市值", 0)),
            frozen_cash=_to_decimal(raw.get("冻结金额", 0)),
        )

    def get_today_orders(self) -> list[Order]:
        """查询当日委托。"""
        self._ensure_connected()
        raw_orders = self._client.today_entrusts
        orders: list[Order] = []
        for o in raw_orders:
            side_str = str(o.get("操作", ""))
            side = OrderSide.BUY if "买" in side_str else OrderSide.SELL
            status_str = str(o.get("备注", ""))
            status = _STATUS_MAP.get(status_str, OrderStatus.PENDING)
            orders.append(Order(
                order_id=str(o.get("合同编号", "")),
                symbol=str(o.get("证券代码", "")),
                side=side,
                quantity=int(o.get("委托数量", 0)),
                price=_to_decimal(o.get("委托价格", 0)),
                filled_quantity=int(o.get("成交数量", 0)),
                avg_price=_to_decimal(o.get("成交均价", 0)),
                status=status,
                order_type=OrderType.LIMIT,
            ))
        return orders
