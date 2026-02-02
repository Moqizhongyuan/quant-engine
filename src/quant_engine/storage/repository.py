"""
数据仓库模块

提供数据模型的 CRUD 操作。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from quant_engine.models.order import Order, OrderDirection, OrderStatus, OrderType
from quant_engine.models.position import Position
from quant_engine.models.signal import SignalDirection, TradingSignal
from quant_engine.storage.database import (
    OrderTable,
    PositionTable,
    SignalTable,
    TradeLogTable,
    get_database,
)
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


class OrderRepository:
    """订单仓库"""

    def __init__(self, session: Optional[Session] = None):
        """
        初始化订单仓库。

        Args:
            session: 数据库会话，None 则使用默认会话
        """
        self._session = session

    def _get_session(self) -> Session:
        """获取会话"""
        if self._session:
            return self._session
        return get_database().get_session()

    def _to_model(self, row: OrderTable) -> Order:
        """将数据库行转换为模型"""
        return Order(
            id=UUID(row.id),
            symbol=row.symbol,
            direction=OrderDirection(row.direction.value if hasattr(row.direction, 'value') else row.direction),
            quantity=row.quantity,
            price=Decimal(str(row.price)) if row.price else None,
            order_type=OrderType(row.order_type.value if hasattr(row.order_type, 'value') else row.order_type),
            status=OrderStatus(row.status.value if hasattr(row.status, 'value') else row.status),
            filled_quantity=row.filled_quantity or 0,
            filled_price=Decimal(str(row.filled_price)) if row.filled_price else None,
            broker_order_id=row.broker_order_id,
            signal_id=UUID(row.signal_id) if row.signal_id else None,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_row(self, order: Order) -> OrderTable:
        """将模型转换为数据库行"""
        return OrderTable(
            id=str(order.id),
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=float(order.price) if order.price else None,
            order_type=order.order_type,
            status=order.status,
            filled_quantity=order.filled_quantity,
            filled_price=float(order.filled_price) if order.filled_price else None,
            broker_order_id=order.broker_order_id,
            signal_id=str(order.signal_id) if order.signal_id else None,
            error_message=order.error_message,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def save(self, order: Order) -> Order:
        """
        保存订单。

        Args:
            order: 订单模型

        Returns:
            保存后的订单
        """
        session = self._get_session()
        try:
            existing = session.query(OrderTable).filter(OrderTable.id == str(order.id)).first()
            if existing:
                existing.status = order.status
                existing.filled_quantity = order.filled_quantity
                existing.filled_price = float(order.filled_price) if order.filled_price else None
                existing.broker_order_id = order.broker_order_id
                existing.error_message = order.error_message
                existing.updated_at = datetime.now()
            else:
                row = self._to_row(order)
                session.add(row)
            session.commit()
            logger.debug(f"订单已保存: {order.id}")
            return order
        except Exception as e:
            session.rollback()
            logger.error(f"保存订单失败: {e}")
            raise
        finally:
            if not self._session:
                session.close()

    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """
        根据ID获取订单。

        Args:
            order_id: 订单ID

        Returns:
            订单模型或 None
        """
        session = self._get_session()
        try:
            row = session.query(OrderTable).filter(OrderTable.id == str(order_id)).first()
            return self._to_model(row) if row else None
        finally:
            if not self._session:
                session.close()

    def get_by_status(self, status: OrderStatus) -> List[Order]:
        """
        根据状态获取订单列表。

        Args:
            status: 订单状态

        Returns:
            订单列表
        """
        session = self._get_session()
        try:
            rows = (
                session.query(OrderTable)
                .filter(OrderTable.status == status)
                .order_by(desc(OrderTable.created_at))
                .all()
            )
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()

    def get_pending_orders(self) -> List[Order]:
        """获取待处理订单"""
        return self.get_by_status(OrderStatus.PENDING)

    def get_active_orders(self) -> List[Order]:
        """获取活跃订单（已提交但未完成）"""
        session = self._get_session()
        try:
            rows = (
                session.query(OrderTable)
                .filter(
                    OrderTable.status.in_([
                        OrderStatus.SUBMITTED,
                        OrderStatus.PARTIAL_FILLED,
                    ])
                )
                .order_by(desc(OrderTable.created_at))
                .all()
            )
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()

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
        session = self._get_session()
        try:
            query = session.query(OrderTable)

            if symbol:
                query = query.filter(OrderTable.symbol == symbol)
            if start_date:
                query = query.filter(OrderTable.created_at >= start_date)
            if end_date:
                query = query.filter(OrderTable.created_at <= end_date)

            rows = query.order_by(desc(OrderTable.created_at)).limit(limit).all()
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()


class PositionRepository:
    """持仓仓库"""

    def __init__(self, session: Optional[Session] = None):
        """
        初始化持仓仓库。

        Args:
            session: 数据库会话
        """
        self._session = session

    def _get_session(self) -> Session:
        """获取会话"""
        if self._session:
            return self._session
        return get_database().get_session()

    def _to_model(self, row: PositionTable) -> Position:
        """将数据库行转换为模型"""
        return Position(
            id=UUID(row.id),
            symbol=row.symbol,
            name=row.name,
            quantity=row.quantity or 0,
            available_quantity=row.available_quantity or 0,
            frozen_quantity=row.frozen_quantity or 0,
            avg_cost=Decimal(str(row.avg_cost)) if row.avg_cost else Decimal("0"),
            current_price=Decimal(str(row.current_price)) if row.current_price else Decimal("0"),
            updated_at=row.updated_at,
        )

    def _to_row(self, position: Position) -> PositionTable:
        """将模型转换为数据库行"""
        return PositionTable(
            id=str(position.id),
            symbol=position.symbol,
            name=position.name,
            quantity=position.quantity,
            available_quantity=position.available_quantity,
            frozen_quantity=position.frozen_quantity,
            avg_cost=float(position.avg_cost),
            current_price=float(position.current_price),
            updated_at=position.updated_at,
        )

    def save(self, position: Position) -> Position:
        """
        保存持仓。

        Args:
            position: 持仓模型

        Returns:
            保存后的持仓
        """
        session = self._get_session()
        try:
            existing = (
                session.query(PositionTable)
                .filter(PositionTable.symbol == position.symbol)
                .first()
            )
            if existing:
                existing.quantity = position.quantity
                existing.available_quantity = position.available_quantity
                existing.frozen_quantity = position.frozen_quantity
                existing.avg_cost = float(position.avg_cost)
                existing.current_price = float(position.current_price)
                existing.name = position.name
                existing.updated_at = datetime.now()
            else:
                row = self._to_row(position)
                session.add(row)
            session.commit()
            logger.debug(f"持仓已保存: {position.symbol}")
            return position
        except Exception as e:
            session.rollback()
            logger.error(f"保存持仓失败: {e}")
            raise
        finally:
            if not self._session:
                session.close()

    def get_by_symbol(self, symbol: str) -> Optional[Position]:
        """
        根据股票代码获取持仓。

        Args:
            symbol: 股票代码

        Returns:
            持仓模型或 None
        """
        session = self._get_session()
        try:
            row = session.query(PositionTable).filter(PositionTable.symbol == symbol).first()
            return self._to_model(row) if row else None
        finally:
            if not self._session:
                session.close()

    def list_positions(self) -> List[Position]:
        """
        获取所有持仓。

        Returns:
            持仓列表
        """
        session = self._get_session()
        try:
            rows = (
                session.query(PositionTable)
                .filter(PositionTable.quantity > 0)
                .order_by(PositionTable.symbol)
                .all()
            )
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()

    def delete_by_symbol(self, symbol: str) -> bool:
        """
        删除持仓记录。

        Args:
            symbol: 股票代码

        Returns:
            是否删除成功
        """
        session = self._get_session()
        try:
            result = session.query(PositionTable).filter(PositionTable.symbol == symbol).delete()
            session.commit()
            return result > 0
        except Exception as e:
            session.rollback()
            logger.error(f"删除持仓失败: {e}")
            raise
        finally:
            if not self._session:
                session.close()


class SignalRepository:
    """信号仓库"""

    def __init__(self, session: Optional[Session] = None):
        """
        初始化信号仓库。

        Args:
            session: 数据库会话
        """
        self._session = session

    def _get_session(self) -> Session:
        """获取会话"""
        if self._session:
            return self._session
        return get_database().get_session()

    def _to_model(self, row: SignalTable) -> TradingSignal:
        """将数据库行转换为模型"""
        return TradingSignal(
            id=UUID(row.id),
            symbol=row.symbol,
            name=row.name,
            direction=SignalDirection(row.direction.value if hasattr(row.direction, 'value') else row.direction),
            target_quantity=row.target_quantity,
            target_price=Decimal(str(row.target_price)) if row.target_price else None,
            target_ratio=Decimal(str(row.target_ratio)) if row.target_ratio else None,
            source=row.source,
            strategy_name=row.strategy_name,
            reason=row.reason,
            executed=row.executed or False,
            order_id=UUID(row.order_id) if row.order_id else None,
            created_at=row.created_at,
            executed_at=row.executed_at,
        )

    def _to_row(self, signal: TradingSignal) -> SignalTable:
        """将模型转换为数据库行"""
        return SignalTable(
            id=str(signal.id),
            symbol=signal.symbol,
            name=signal.name,
            direction=signal.direction,
            target_quantity=signal.target_quantity,
            target_price=float(signal.target_price) if signal.target_price else None,
            target_ratio=float(signal.target_ratio) if signal.target_ratio else None,
            source=signal.source,
            strategy_name=signal.strategy_name,
            reason=signal.reason,
            executed=signal.executed,
            order_id=str(signal.order_id) if signal.order_id else None,
            created_at=signal.created_at,
            executed_at=signal.executed_at,
        )

    def save(self, signal: TradingSignal) -> TradingSignal:
        """
        保存信号。

        Args:
            signal: 信号模型

        Returns:
            保存后的信号
        """
        session = self._get_session()
        try:
            existing = session.query(SignalTable).filter(SignalTable.id == str(signal.id)).first()
            if existing:
                existing.executed = signal.executed
                existing.order_id = str(signal.order_id) if signal.order_id else None
                existing.executed_at = signal.executed_at
            else:
                row = self._to_row(signal)
                session.add(row)
            session.commit()
            logger.debug(f"信号已保存: {signal.id}")
            return signal
        except Exception as e:
            session.rollback()
            logger.error(f"保存信号失败: {e}")
            raise
        finally:
            if not self._session:
                session.close()

    def save_batch(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """
        批量保存信号。

        Args:
            signals: 信号列表

        Returns:
            保存后的信号列表
        """
        session = self._get_session()
        try:
            for signal in signals:
                row = self._to_row(signal)
                session.merge(row)
            session.commit()
            logger.info(f"批量保存 {len(signals)} 个信号")
            return signals
        except Exception as e:
            session.rollback()
            logger.error(f"批量保存信号失败: {e}")
            raise
        finally:
            if not self._session:
                session.close()

    def get_by_id(self, signal_id: UUID) -> Optional[TradingSignal]:
        """
        根据ID获取信号。

        Args:
            signal_id: 信号ID

        Returns:
            信号模型或 None
        """
        session = self._get_session()
        try:
            row = session.query(SignalTable).filter(SignalTable.id == str(signal_id)).first()
            return self._to_model(row) if row else None
        finally:
            if not self._session:
                session.close()

    def get_pending_signals(self) -> List[TradingSignal]:
        """
        获取待执行信号。

        Returns:
            信号列表
        """
        session = self._get_session()
        try:
            rows = (
                session.query(SignalTable)
                .filter(SignalTable.executed == False)
                .order_by(desc(SignalTable.created_at))
                .all()
            )
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()

    def list_signals(
        self,
        source: Optional[str] = None,
        executed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TradingSignal]:
        """
        查询信号列表。

        Args:
            source: 信号来源筛选
            executed: 是否已执行筛选
            start_date: 开始日期
            limit: 返回数量限制

        Returns:
            信号列表
        """
        session = self._get_session()
        try:
            query = session.query(SignalTable)

            if source:
                query = query.filter(SignalTable.source == source)
            if executed is not None:
                query = query.filter(SignalTable.executed == executed)
            if start_date:
                query = query.filter(SignalTable.created_at >= start_date)

            rows = query.order_by(desc(SignalTable.created_at)).limit(limit).all()
            return [self._to_model(row) for row in rows]
        finally:
            if not self._session:
                session.close()


class TradeLogRepository:
    """交易日志仓库"""

    def __init__(self, session: Optional[Session] = None):
        """
        初始化日志仓库。

        Args:
            session: 数据库会话
        """
        self._session = session

    def _get_session(self) -> Session:
        """获取会话"""
        if self._session:
            return self._session
        return get_database().get_session()

    def log(self, level: str, message: str, context: Optional[dict] = None) -> None:
        """
        记录交易日志。

        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文数据
        """
        session = self._get_session()
        try:
            row = TradeLogTable(
                level=level,
                message=message,
                context=context,
                created_at=datetime.now(),
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"记录交易日志失败: {e}")
        finally:
            if not self._session:
                session.close()

    def info(self, message: str, context: Optional[dict] = None) -> None:
        """记录 INFO 级别日志"""
        self.log("INFO", message, context)

    def warning(self, message: str, context: Optional[dict] = None) -> None:
        """记录 WARNING 级别日志"""
        self.log("WARNING", message, context)

    def error(self, message: str, context: Optional[dict] = None) -> None:
        """记录 ERROR 级别日志"""
        self.log("ERROR", message, context)

    def get_logs(
        self,
        level: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        查询交易日志。

        Args:
            level: 日志级别筛选
            start_date: 开始日期
            limit: 返回数量限制

        Returns:
            日志列表
        """
        session = self._get_session()
        try:
            query = session.query(TradeLogTable)

            if level:
                query = query.filter(TradeLogTable.level == level)
            if start_date:
                query = query.filter(TradeLogTable.created_at >= start_date)

            rows = query.order_by(desc(TradeLogTable.created_at)).limit(limit).all()
            return [
                {
                    "id": row.id,
                    "level": row.level,
                    "message": row.message,
                    "context": row.context,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        finally:
            if not self._session:
                session.close()
