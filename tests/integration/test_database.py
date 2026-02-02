"""
数据库集成测试
"""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from quant_engine.models.order import Order, OrderDirection, OrderStatus, OrderType
from quant_engine.models.position import Position
from quant_engine.models.signal import SignalDirection, TradingSignal
from quant_engine.storage.database import Database
from quant_engine.storage.repository import (
    OrderRepository,
    PositionRepository,
    SignalRepository,
)


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(url=f"sqlite:///{db_path}")
        db.create_tables()
        yield db


@pytest.fixture
def order_repo(temp_db):
    """订单仓库"""
    return OrderRepository()


@pytest.fixture
def position_repo(temp_db):
    """持仓仓库"""
    return PositionRepository()


@pytest.fixture
def signal_repo(temp_db):
    """信号仓库"""
    return SignalRepository()


class TestOrderRepository:
    """订单仓库测试"""

    def test_save_and_get_order(self, order_repo):
        """测试保存和获取订单"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
            price=Decimal("10.50"),
            order_type=OrderType.LIMIT,
        )

        saved = order_repo.save(order)
        assert saved.id == order.id

        retrieved = order_repo.get_by_id(order.id)
        assert retrieved is not None
        assert retrieved.symbol == "000001.XSHE"
        assert retrieved.quantity == 1000

    def test_update_order_status(self, order_repo):
        """测试更新订单状态"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
        )
        order_repo.save(order)

        order.update_status(OrderStatus.FILLED)
        order.filled_quantity = 1000
        order_repo.save(order)

        retrieved = order_repo.get_by_id(order.id)
        assert retrieved.status == OrderStatus.FILLED
        assert retrieved.filled_quantity == 1000

    def test_list_orders(self, order_repo):
        """测试查询订单列表"""
        for i in range(5):
            order = Order(
                symbol=f"00000{i}.XSHE",
                direction=OrderDirection.BUY,
                quantity=1000,
            )
            order_repo.save(order)

        orders = order_repo.list_orders(limit=10)
        assert len(orders) == 5


class TestPositionRepository:
    """持仓仓库测试"""

    def test_save_and_get_position(self, position_repo):
        """测试保存和获取持仓"""
        position = Position(
            symbol="000001.XSHE",
            name="平安银行",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.50"),
        )

        position_repo.save(position)

        retrieved = position_repo.get_by_symbol("000001.XSHE")
        assert retrieved is not None
        assert retrieved.quantity == 10000

    def test_update_position(self, position_repo):
        """测试更新持仓"""
        position = Position(
            symbol="000001.XSHE",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.00"),
        )
        position_repo.save(position)

        position.quantity = 15000
        position.current_price = Decimal("11.00")
        position_repo.save(position)

        retrieved = position_repo.get_by_symbol("000001.XSHE")
        assert retrieved.quantity == 15000
        assert retrieved.current_price == Decimal("11.00")

    def test_list_positions(self, position_repo):
        """测试查询持仓列表"""
        for i in range(3):
            position = Position(
                symbol=f"00000{i}.XSHE",
                quantity=1000 * (i + 1),
                avg_cost=Decimal("10.00"),
                current_price=Decimal("10.00"),
            )
            position_repo.save(position)

        positions = position_repo.list_positions()
        assert len(positions) == 3


class TestSignalRepository:
    """信号仓库测试"""

    def test_save_and_get_signal(self, signal_repo):
        """测试保存和获取信号"""
        signal = TradingSignal(
            symbol="000001.XSHE",
            direction=SignalDirection.BUY,
            target_quantity=1000,
            source="joinquant",
        )

        signal_repo.save(signal)

        retrieved = signal_repo.get_by_id(signal.id)
        assert retrieved is not None
        assert retrieved.symbol == "000001.XSHE"

    def test_get_pending_signals(self, signal_repo):
        """测试获取待执行信号"""
        for i in range(3):
            signal = TradingSignal(
                symbol=f"00000{i}.XSHE",
                direction=SignalDirection.BUY,
                target_quantity=1000,
            )
            if i == 0:
                signal.executed = True
            signal_repo.save(signal)

        pending = signal_repo.get_pending_signals()
        assert len(pending) == 2

    def test_batch_save_signals(self, signal_repo):
        """测试批量保存信号"""
        signals = [
            TradingSignal(
                symbol=f"00000{i}.XSHE",
                direction=SignalDirection.BUY,
                target_quantity=1000,
            )
            for i in range(5)
        ]

        signal_repo.save_batch(signals)

        all_signals = signal_repo.list_signals(limit=10)
        assert len(all_signals) == 5
