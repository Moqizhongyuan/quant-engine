"""
miniQMT 交易接口适配器

封装 miniQMT SDK，提供统一的交易接口。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from quant_engine.adapters.broker.base import Broker, OrderResult
from quant_engine.models.account import Account
from quant_engine.models.order import Order, OrderDirection, OrderStatus, OrderType
from quant_engine.models.position import Position
from quant_engine.utils.config import get_settings
from quant_engine.utils.exceptions import (
    AuthenticationError,
    BrokerNotConnectedError,
    ConnectionError,
    OrderCancelError,
    OrderSubmitError,
)
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


class MiniQMTBroker(Broker):
    """
    miniQMT 交易接口适配器。

    封装 miniQMT/QMT SDK，提供订单提交、撤单、查询等功能。
    """

    def __init__(
        self,
        path: Optional[str] = None,
        account_id: Optional[str] = None,
        simulation: bool = True,
        timeout: int = 10,
    ):
        """
        初始化 miniQMT 适配器。

        Args:
            path: QMT 安装路径
            account_id: 账户ID
            simulation: 是否模拟交易
            timeout: 连接超时秒数
        """
        settings = get_settings()
        qmt_config = settings.broker.miniqmt

        self._path = path or qmt_config.path
        self._account_id = account_id or qmt_config.account_id
        self._simulation = simulation if simulation is not None else qmt_config.simulation
        self._timeout = timeout or qmt_config.timeout

        self._connected = False
        self._xt_trader = None
        self._callback = None

    @property
    def name(self) -> str:
        """接口名称"""
        return "miniQMT"

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    @property
    def is_simulation(self) -> bool:
        """是否为模拟交易"""
        return self._simulation

    def connect(self) -> bool:
        """
        连接 miniQMT。

        Returns:
            是否连接成功

        Raises:
            ConnectionError: 连接失败
            AuthenticationError: 认证失败
        """
        if self._connected:
            return True

        if self._simulation:
            logger.info("miniQMT 模拟模式已启用")
            self._connected = True
            return True

        try:
            from xtquant import xttrader
            from xtquant.xttype import StockAccount

            self._xt_trader = xttrader.XtQuantTrader(self._path, self._account_id)

            # 创建回调
            self._callback = _QMTCallback()
            self._xt_trader.register_callback(self._callback)

            # 启动交易线程
            self._xt_trader.start()

            # 连接服务器
            connect_result = self._xt_trader.connect()
            if connect_result != 0:
                raise ConnectionError(f"连接 miniQMT 服务器失败，错误码: {connect_result}")

            # 订阅账户
            account = StockAccount(self._account_id)
            subscribe_result = self._xt_trader.subscribe(account)
            if subscribe_result != 0:
                raise AuthenticationError(f"订阅账户失败，错误码: {subscribe_result}")

            self._connected = True
            logger.info(f"miniQMT 连接成功，账户: {self._account_id}")
            return True

        except ImportError:
            raise ConnectionError("未安装 xtquant 模块，请先安装 miniQMT SDK")
        except Exception as e:
            raise ConnectionError(f"连接 miniQMT 失败: {e}")

    def disconnect(self) -> None:
        """断开连接"""
        if self._xt_trader:
            try:
                self._xt_trader.stop()
            except Exception as e:
                logger.warning(f"断开 miniQMT 连接时出错: {e}")
            self._xt_trader = None

        self._connected = False
        logger.info("miniQMT 连接已断开")

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
        if not self._connected:
            raise BrokerNotConnectedError()

        # 模拟模式
        if self._simulation:
            return self._simulate_submit_order(order)

        try:
            from xtquant.xttype import StockAccount

            account = StockAccount(self._account_id)

            # 转换订单方向
            if order.direction == OrderDirection.BUY:
                order_type = 23  # 买入
            else:
                order_type = 24  # 卖出

            # 转换价格类型
            if order.order_type == OrderType.MARKET:
                price_type = 5  # 市价
                price = 0
            else:
                price_type = 11  # 限价
                price = float(order.price) if order.price else 0

            # 提交订单
            order_id = self._xt_trader.order_stock(
                account,
                order.symbol,
                order_type,
                order.quantity,
                price_type,
                price,
            )

            if order_id < 0:
                raise OrderSubmitError(f"订单提交失败，错误码: {order_id}")

            logger.info(f"订单已提交: {order.symbol} {order.direction.value} {order.quantity}股, 券商订单号: {order_id}")

            return OrderResult(
                success=True,
                broker_order_id=str(order_id),
                message="订单提交成功",
            )

        except ImportError:
            raise OrderSubmitError("未安装 xtquant 模块")
        except Exception as e:
            raise OrderSubmitError(f"订单提交失败: {e}")

    def _simulate_submit_order(self, order: Order) -> OrderResult:
        """
        模拟提交订单。

        Args:
            order: 订单对象

        Returns:
            模拟的订单结果
        """
        broker_order_id = f"SIM_{uuid4().hex[:8].upper()}"
        logger.info(
            f"[模拟] 订单已提交: {order.symbol} {order.direction.value} "
            f"{order.quantity}股 @ {order.price}, 订单号: {broker_order_id}"
        )

        return OrderResult(
            success=True,
            broker_order_id=broker_order_id,
            message="[模拟] 订单提交成功",
        )

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
        if not self._connected:
            raise BrokerNotConnectedError()

        if self._simulation:
            logger.info(f"[模拟] 订单已撤销: {order_id}")
            return True

        try:
            from xtquant.xttype import StockAccount

            account = StockAccount(self._account_id)
            result = self._xt_trader.cancel_order_stock(account, int(order_id))

            if result != 0:
                raise OrderCancelError(f"撤单失败，错误码: {result}")

            logger.info(f"订单已撤销: {order_id}")
            return True

        except Exception as e:
            raise OrderCancelError(f"撤单失败: {e}")

    def query_order(self, order_id: str) -> Optional[Order]:
        """
        查询订单状态。

        Args:
            order_id: 券商订单号

        Returns:
            订单对象或 None
        """
        if not self._connected:
            raise BrokerNotConnectedError()

        if self._simulation:
            return None

        try:
            from xtquant.xttype import StockAccount

            account = StockAccount(self._account_id)
            orders = self._xt_trader.query_stock_orders(account)

            for o in orders:
                if str(o.order_id) == order_id:
                    return self._convert_order(o)

            return None

        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return None

    def get_positions(self) -> List[Position]:
        """
        查询持仓。

        Returns:
            持仓列表
        """
        if not self._connected:
            raise BrokerNotConnectedError()

        if self._simulation:
            return self._get_simulated_positions()

        try:
            from xtquant.xttype import StockAccount

            account = StockAccount(self._account_id)
            positions = self._xt_trader.query_stock_positions(account)

            result = []
            for p in positions:
                if p.volume > 0:
                    position = Position(
                        symbol=p.stock_code,
                        quantity=p.volume,
                        available_quantity=p.can_use_volume,
                        frozen_quantity=p.volume - p.can_use_volume,
                        avg_cost=Decimal(str(p.avg_price)),
                        current_price=Decimal(str(p.market_value / p.volume)) if p.volume > 0 else Decimal("0"),
                    )
                    result.append(position)

            return result

        except Exception as e:
            logger.error(f"查询持仓失败: {e}")
            return []

    def _get_simulated_positions(self) -> List[Position]:
        """获取模拟持仓"""
        return []

    def get_account(self) -> Account:
        """
        查询账户信息。

        Returns:
            账户对象
        """
        if not self._connected:
            raise BrokerNotConnectedError()

        if self._simulation:
            return self._get_simulated_account()

        try:
            from xtquant.xttype import StockAccount

            account = StockAccount(self._account_id)
            asset = self._xt_trader.query_stock_asset(account)

            return Account(
                account_id=self._account_id,
                total_asset=Decimal(str(asset.total_asset)),
                cash=Decimal(str(asset.cash)),
                frozen_cash=Decimal(str(asset.frozen_cash)),
                market_value=Decimal(str(asset.market_value)),
            )

        except Exception as e:
            logger.error(f"查询账户失败: {e}")
            return Account(account_id=self._account_id)

    def _get_simulated_account(self) -> Account:
        """获取模拟账户"""
        return Account(
            account_id=f"SIM_{self._account_id or 'DEFAULT'}",
            total_asset=Decimal("1000000"),
            cash=Decimal("1000000"),
            frozen_cash=Decimal("0"),
            market_value=Decimal("0"),
        )

    def _convert_order(self, qmt_order) -> Order:
        """
        将 QMT 订单转换为内部订单模型。

        Args:
            qmt_order: QMT 订单对象

        Returns:
            Order 对象
        """
        # 转换订单方向
        if qmt_order.order_type == 23:
            direction = OrderDirection.BUY
        else:
            direction = OrderDirection.SELL

        # 转换订单状态
        status_map = {
            48: OrderStatus.PENDING,  # 未报
            49: OrderStatus.SUBMITTED,  # 待报
            50: OrderStatus.SUBMITTED,  # 已报
            51: OrderStatus.SUBMITTED,  # 已报待撤
            52: OrderStatus.PARTIAL_FILLED,  # 部成待撤
            53: OrderStatus.PARTIAL_FILLED,  # 部撤
            54: OrderStatus.CANCELLED,  # 已撤
            55: OrderStatus.PARTIAL_FILLED,  # 部成
            56: OrderStatus.FILLED,  # 已成
            57: OrderStatus.REJECTED,  # 废单
        }
        status = status_map.get(qmt_order.order_status, OrderStatus.PENDING)

        return Order(
            symbol=qmt_order.stock_code,
            direction=direction,
            quantity=qmt_order.order_volume,
            price=Decimal(str(qmt_order.price)),
            order_type=OrderType.LIMIT,
            status=status,
            filled_quantity=qmt_order.traded_volume,
            filled_price=Decimal(str(qmt_order.traded_price)) if qmt_order.traded_price else None,
            broker_order_id=str(qmt_order.order_id),
            created_at=datetime.now(),
        )


class _QMTCallback:
    """QMT 回调处理类"""

    def on_disconnected(self):
        """断开连接回调"""
        logger.warning("miniQMT 连接已断开")

    def on_stock_order(self, order):
        """订单状态变化回调"""
        logger.info(f"订单状态更新: {order.stock_code} 状态={order.order_status}")

    def on_stock_trade(self, trade):
        """成交回调"""
        logger.info(f"成交通知: {trade.stock_code} 成交{trade.traded_volume}股 @ {trade.traded_price}")

    def on_order_error(self, order, error_msg):
        """订单错误回调"""
        logger.error(f"订单错误: {order.stock_code} - {error_msg}")

    def on_cancel_error(self, order, error_msg):
        """撤单错误回调"""
        logger.error(f"撤单错误: {order.order_id} - {error_msg}")
