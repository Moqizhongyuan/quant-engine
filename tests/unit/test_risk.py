"""
风控模块单元测试
"""

from decimal import Decimal

import pytest

from quant_engine.core.risk import RiskCheckResult, RiskManager
from quant_engine.models.account import Account
from quant_engine.models.order import Order, OrderDirection, OrderType
from quant_engine.models.position import Position
from quant_engine.utils.config import RiskConfig


@pytest.fixture
def risk_config():
    """风控配置"""
    return RiskConfig(
        enabled=True,
        max_position_ratio=0.2,
        max_daily_loss_ratio=0.05,
        stop_loss_ratio=0.08,
        take_profit_ratio=0.20,
        max_holdings=10,
        max_order_amount=100000,
    )


@pytest.fixture
def risk_manager(risk_config):
    """风控管理器"""
    return RiskManager(risk_config)


@pytest.fixture
def account():
    """测试账户"""
    return Account(
        account_id="TEST001",
        total_asset=Decimal("1000000"),
        cash=Decimal("500000"),
        frozen_cash=Decimal("0"),
        market_value=Decimal("500000"),
    )


@pytest.fixture
def positions():
    """测试持仓"""
    return [
        Position(
            symbol="000001.XSHE",
            name="平安银行",
            quantity=10000,
            available_quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("10.50"),
        ),
        Position(
            symbol="600000.XSHG",
            name="浦发银行",
            quantity=5000,
            available_quantity=5000,
            avg_cost=Decimal("8.00"),
            current_price=Decimal("7.50"),
        ),
    ]


class TestRiskManager:
    """风控管理器测试"""

    def test_check_order_amount_pass(self, risk_manager, account, positions):
        """测试单笔金额检查通过"""
        order = Order(
            symbol="000002.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
            price=Decimal("50.00"),
            order_type=OrderType.LIMIT,
        )

        result = risk_manager._check_order_amount(order)
        assert result.passed is True

    def test_check_order_amount_fail(self, risk_manager, account, positions):
        """测试单笔金额检查失败"""
        order = Order(
            symbol="000002.XSHE",
            direction=OrderDirection.BUY,
            quantity=10000,
            price=Decimal("50.00"),
            order_type=OrderType.LIMIT,
        )

        result = risk_manager._check_order_amount(order)
        assert result.passed is False
        assert "超过限制" in result.message

    def test_check_position_limit_pass(self, risk_manager, account, positions):
        """测试持仓比例检查通过"""
        order = Order(
            symbol="000002.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
            price=Decimal("50.00"),
            order_type=OrderType.LIMIT,
        )

        result = risk_manager._check_position_limit(order, account, positions)
        assert result.passed is True

    def test_check_position_limit_fail(self, risk_manager, account, positions):
        """测试持仓比例检查失败"""
        order = Order(
            symbol="000001.XSHE",
            direction=OrderDirection.BUY,
            quantity=20000,
            price=Decimal("10.00"),
            order_type=OrderType.LIMIT,
        )

        result = risk_manager._check_position_limit(order, account, positions)
        assert result.passed is False

    def test_check_holdings_limit_pass(self, risk_manager, positions):
        """测试持仓数量检查通过"""
        order = Order(
            symbol="000002.XSHE",
            direction=OrderDirection.BUY,
            quantity=1000,
            price=Decimal("50.00"),
            order_type=OrderType.LIMIT,
        )

        result = risk_manager._check_holdings_limit(order, positions)
        assert result.passed is True

    def test_check_stop_loss_triggered(self, risk_manager):
        """测试止损触发"""
        position = Position(
            symbol="600000.XSHG",
            quantity=5000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("9.00"),
        )

        result = risk_manager._check_stop_loss(position)
        assert result.passed is False
        assert "止损" in result.message

    def test_check_stop_loss_not_triggered(self, risk_manager):
        """测试止损未触发"""
        position = Position(
            symbol="600000.XSHG",
            quantity=5000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("9.50"),
        )

        result = risk_manager._check_stop_loss(position)
        assert result.passed is True

    def test_check_take_profit_triggered(self, risk_manager):
        """测试止盈触发"""
        position = Position(
            symbol="000001.XSHE",
            quantity=10000,
            avg_cost=Decimal("10.00"),
            current_price=Decimal("12.50"),
        )

        result = risk_manager._check_take_profit(position)
        assert result.passed is False
        assert "止盈" in result.message

    def test_disabled_risk_manager(self, account, positions):
        """测试禁用风控"""
        config = RiskConfig(enabled=False)
        manager = RiskManager(config)

        order = Order(
            symbol="000002.XSHE",
            direction=OrderDirection.BUY,
            quantity=100000,
            price=Decimal("100.00"),
            order_type=OrderType.LIMIT,
        )

        result = manager.check_order(order, account, positions)
        assert result.passed is True
        assert result.rule == "disabled"

    def test_check_all(self, risk_manager, account, positions):
        """测试全部检查"""
        results = risk_manager.check_all(account, positions)
        assert len(results) > 0
        assert all(isinstance(r, RiskCheckResult) for r in results)
