"""
数据模型单元测试
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from quant_engine.models.order import Order, OrderDirection, OrderStatus, OrderType
from quant_engine.models.position import Position
from quant_engine.models.signal import SignalDirection, TradingSignal
from quant_engine.models.account import Account


class TestOrder:
    """订单模型测试"""

    def test_create_order(self):
        """测试创建订单"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
            price=Decimal("10.50"),
            order_type=OrderType.LIMIT,
        )

        assert order.symbol == "000001.XSHE"
        assert order.direction == OrderDirection.BUY
        assert order.quantity == 1000
        assert order.price == Decimal("10.50")
        assert order.status == OrderStatus.PENDING
        assert isinstance(order.id, UUID)

    def test_order_is_completed(self):
        """测试订单完成状态"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
        )

        assert order.is_completed is False

        order.status = OrderStatus.FILLED
        assert order.is_completed is True

        order.status = OrderStatus.CANCELLED
        assert order.is_completed is True

    def test_order_unfilled_quantity(self):
        """测试未成交数量"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
        )
        order.filled_quantity = 300

        assert order.unfilled_quantity == 700

    def test_update_status(self):
        """测试更新状态"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
        )

        order.update_status(OrderStatus.REJECTED, "余额不足")

        assert order.status == OrderStatus.REJECTED
        assert order.error_message == "余额不足"


class TestPosition:
    """持仓模型测试"""

    def test_create_position(self):
        """测试创建持仓"""
        position = Position(
            symbol="000001.XSHE",
            name="平安银行",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.50"),
        )

        assert position.symbol == "000001.XSHE"
        assert position.quantity == 10000

    def test_position_market_value(self):
        """测试市值计算"""
        position = Position(
            symbol="000001.XSHE",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.50"),
        )

        assert position.market_value == Decimal("105000")

    def test_position_profit_loss(self):
        """测试盈亏计算"""
        position = Position(
            symbol="000001.XSHE",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.50"),
        )

        assert position.profit_loss == Decimal("5000")
        assert position.profit_loss_ratio == Decimal("0.0500")

    def test_position_loss(self):
        """测试亏损计算"""
        position = Position(
            symbol="000001.XSHE",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("9.00"),
        )

        assert position.profit_loss == Decimal("-10000")
        assert position.profit_loss_ratio == Decimal("-0.1000")


class TestTradingSignal:
    """交易信号模型测试"""

    def test_create_signal(self):
        """测试创建信号"""
        signal = TradingSignal(
            symbol="000001.XSHE",
            direction=SignalDirection.BUY,
            target_quantity=1000,
            source="joinquant",
        )

        assert signal.symbol == "000001.XSHE"
        assert signal.direction == SignalDirection.BUY
        assert signal.target_quantity == 1000
        assert signal.executed is False

    def test_mark_executed(self):
        """测试标记已执行"""
        signal = TradingSignal(
            symbol="000001.XSHE",
            direction=SignalDirection.BUY,
            target_quantity=1000,
        )

        order_id = UUID("12345678-1234-5678-1234-567812345678")
        signal.mark_executed(order_id)

        assert signal.executed is True
        assert signal.order_id == order_id
        assert signal.executed_at is not None


class TestAccount:
    """账户模型测试"""

    def test_create_account(self):
        """测试创建账户"""
        account = Account(
            account_id="TEST001",
            total_asset=Decimal("1000000"),
            cash=Decimal("500000"),
            market_value=Decimal("500000"),
        )

        assert account.account_id == "TEST001"
        assert account.total_asset == Decimal("1000000")

    def test_available_cash(self):
        """测试可用资金"""
        account = Account(
            account_id="TEST001",
            cash=Decimal("500000"),
            frozen_cash=Decimal("100000"),
        )

        assert account.available_cash == Decimal("400000")

    def test_position_ratio(self):
        """测试仓位比例"""
        account = Account(
            account_id="TEST001",
            total_asset=Decimal("1000000"),
            market_value=Decimal("600000"),
        )

        assert account.position_ratio == Decimal("0.6000")
