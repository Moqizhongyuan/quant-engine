"""
订单执行器

负责订单的提交、状态同步和管理。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from quant_engine.adapters.broker import Broker, OrderResult
from quant_engine.core.risk import RiskManager
from quant_engine.models.account import Account
from quant_engine.models.order import Order, OrderDirection, OrderStatus, OrderType
from quant_engine.models.position import Position
from quant_engine.models.signal import SignalDirection, TradingSignal
from quant_engine.storage.repository import OrderRepository, PositionRepository, TradeLogRepository
from quant_engine.utils.exceptions import OrderSubmitError, RiskControlError
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


class OrderExecutor:
    """
    订单执行器。

    负责将交易信号转换为订单并提交到券商。
    """

    def __init__(
        self,
        broker: Broker,
        risk_manager: Optional[RiskManager] = None,
        order_repo: Optional[OrderRepository] = None,
        position_repo: Optional[PositionRepository] = None,
        trade_log_repo: Optional[TradeLogRepository] = None,
    ):
        """
        初始化订单执行器。

        Args:
            broker: 交易接口
            risk_manager: 风控管理器
            order_repo: 订单仓库
            position_repo: 持仓仓库
            trade_log_repo: 交易日志仓库
        """
        self._broker = broker
        self._risk_manager = risk_manager or RiskManager()
        self._order_repo = order_repo or OrderRepository()
        self._position_repo = position_repo or PositionRepository()
        self._trade_log_repo = trade_log_repo or TradeLogRepository()

    def execute_signal(
        self,
        signal: TradingSignal,
        account: Optional[Account] = None,
        positions: Optional[List[Position]] = None,
    ) -> Order:
        """
        执行交易信号。

        Args:
            signal: 交易信号
            account: 账户信息（用于风控检查）
            positions: 持仓列表（用于风控检查）

        Returns:
            创建的订单

        Raises:
            RiskControlError: 风控检查不通过
            OrderSubmitError: 订单提交失败
        """
        logger.info(f"执行信号: {signal.symbol} {signal.direction.value} {signal.target_quantity}股")

        order = self._create_order_from_signal(signal)

        if account is None:
            account = self._broker.get_account()
        if positions is None:
            positions = self._broker.get_positions()

        self._risk_manager.validate_order_or_raise(order, account, positions)

        self._order_repo.save(order)

        result = self._submit_order(order)

        if result.success:
            order.broker_order_id = result.broker_order_id
            order.update_status(OrderStatus.SUBMITTED)
            signal.mark_executed(order.id)
            self._trade_log_repo.info(
                f"订单已提交: {order.symbol} {order.direction.value} {order.quantity}股",
                {"order_id": str(order.id), "broker_order_id": result.broker_order_id},
            )
        else:
            order.update_status(OrderStatus.REJECTED, result.message)
            self._trade_log_repo.error(
                f"订单提交失败: {order.symbol} - {result.message}",
                {"order_id": str(order.id)},
            )

        self._order_repo.save(order)
        return order

    def _create_order_from_signal(self, signal: TradingSignal) -> Order:
        """
        从信号创建订单。

        Args:
            signal: 交易信号

        Returns:
            订单对象
        """
        direction = (
            OrderDirection.BUY
            if signal.direction == SignalDirection.BUY
            else OrderDirection.SELL
        )

        order_type = OrderType.LIMIT if signal.target_price else OrderType.MARKET

        return Order(
            symbol=signal.symbol,
            direction=direction,
            quantity=signal.target_quantity,
            price=signal.target_price,
            order_type=order_type,
            signal_id=signal.id,
        )

    def _submit_order(self, order: Order) -> OrderResult:
        """
        提交订单到券商。

        Args:
            order: 订单

        Returns:
            提交结果
        """
        try:
            return self._broker.submit_order(order)
        except Exception as e:
            logger.error(f"订单提交异常: {e}")
            return OrderResult(success=False, message=str(e))

    def submit_order(self, order: Order) -> Order:
        """
        直接提交订单。

        Args:
            order: 订单

        Returns:
            更新后的订单

        Raises:
            OrderSubmitError: 提交失败
        """
        self._order_repo.save(order)

        result = self._submit_order(order)

        if result.success:
            order.broker_order_id = result.broker_order_id
            order.update_status(OrderStatus.SUBMITTED)
        else:
            order.update_status(OrderStatus.REJECTED, result.message)
            raise OrderSubmitError(result.message or "订单提交失败")

        self._order_repo.save(order)
        return order

    def cancel_order(self, order_id: UUID) -> bool:
        """
        撤销订单。

        Args:
            order_id: 订单ID

        Returns:
            是否撤销成功
        """
        order = self._order_repo.get_by_id(order_id)
        if not order:
            logger.warning(f"订单不存在: {order_id}")
            return False

        if order.is_completed:
            logger.warning(f"订单已完成，无法撤销: {order_id}")
            return False

        if not order.broker_order_id:
            order.update_status(OrderStatus.CANCELLED)
            self._order_repo.save(order)
            return True

        try:
            success = self._broker.cancel_order(order.broker_order_id)
            if success:
                order.update_status(OrderStatus.CANCELLED)
                self._order_repo.save(order)
                self._trade_log_repo.info(
                    f"订单已撤销: {order.symbol}",
                    {"order_id": str(order.id)},
                )
            return success
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False

    def sync_order_status(self, order_id: UUID) -> Optional[Order]:
        """
        同步订单状态。

        Args:
            order_id: 订单ID

        Returns:
            更新后的订单或 None
        """
        order = self._order_repo.get_by_id(order_id)
        if not order or not order.broker_order_id:
            return order

        try:
            broker_order = self._broker.query_order(order.broker_order_id)
            if broker_order:
                order.status = broker_order.status
                order.filled_quantity = broker_order.filled_quantity
                order.filled_price = broker_order.filled_price
                order.updated_at = datetime.now()
                self._order_repo.save(order)
        except Exception as e:
            logger.error(f"同步订单状态失败: {e}")

        return order

    def sync_all_active_orders(self) -> List[Order]:
        """
        同步所有活跃订单状态。

        Returns:
            更新后的订单列表
        """
        active_orders = self._order_repo.get_active_orders()
        updated_orders = []

        for order in active_orders:
            updated = self.sync_order_status(order.id)
            if updated:
                updated_orders.append(updated)

        logger.info(f"同步了 {len(updated_orders)} 个活跃订单")
        return updated_orders

    def get_pending_orders(self) -> List[Order]:
        """获取待提交订单"""
        return self._order_repo.get_pending_orders()

    def get_active_orders(self) -> List[Order]:
        """获取活跃订单"""
        return self._order_repo.get_active_orders()

    def list_orders(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """
        查询订单列表。

        Args:
            symbol: 股票代码筛选
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            订单列表
        """
        return self._order_repo.list_orders(symbol, start_date, end_date, limit)
