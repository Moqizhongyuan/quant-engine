"""CLI 参数解析 + 命令分发测试。"""

from __future__ import annotations

import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from common.exceptions import QuantEngineError
from common.types import (
    Account,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from runtime.cli import build_parser, _handle_cancel, _handle_query, _handle_trade


class TestBuildParser:
    """build_parser 参数解析测试。"""

    def test_parse_buy(self):
        """解析 buy 命令。"""
        parser = build_parser()
        args = parser.parse_args([
            "trade", "buy", "--symbol", "000001",
            "--quantity", "500", "--price", "12.50",
        ])
        assert args.command == "trade"
        assert args.action == "buy"
        assert args.symbol == "000001"
        assert args.quantity == 500
        assert args.price == "12.50"

    def test_parse_sell(self):
        """解析 sell 命令。"""
        parser = build_parser()
        args = parser.parse_args([
            "trade", "sell", "--symbol", "600036",
            "--quantity", "200", "--price", "35.00",
        ])
        assert args.action == "sell"
        assert args.symbol == "600036"

    def test_parse_cancel(self):
        """解析 cancel 命令。"""
        parser = build_parser()
        args = parser.parse_args([
            "trade", "cancel", "--order-id", "ORD001",
        ])
        assert args.action == "cancel"
        assert args.order_id == "ORD001"

    def test_parse_query_positions(self):
        """解析 query positions 命令。"""
        parser = build_parser()
        args = parser.parse_args(["query", "positions"])
        assert args.command == "query"
        assert args.target == "positions"

    def test_parse_query_account(self):
        """解析 query account 命令。"""
        parser = build_parser()
        args = parser.parse_args(["query", "account"])
        assert args.target == "account"

    def test_parse_query_orders(self):
        """解析 query orders 命令。"""
        parser = build_parser()
        args = parser.parse_args(["query", "orders"])
        assert args.target == "orders"

    def test_missing_command_exits(self):
        """缺少命令参数退出。"""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_missing_buy_symbol_exits(self):
        """buy 缺少 --symbol 退出。"""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["trade", "buy", "--quantity", "100", "--price", "10"])

    def test_missing_trade_action_exits(self):
        """trade 缺少子命令退出。"""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["trade"])


def _make_namespace(**kwargs):
    """构造 argparse.Namespace 辅助函数。"""
    import argparse
    return argparse.Namespace(**kwargs)


class TestHandleTrade:
    """_handle_trade 测试。"""

    def test_buy_calls_broker(self):
        """buy 操作调用 broker.buy。"""
        mock_broker = MagicMock()
        mock_broker.buy.return_value = OrderResult(
            order_id="B1", symbol="000001", side=OrderSide.BUY,
            quantity=500, price=Decimal("12.50"), status=OrderStatus.SUBMITTED,
        )
        args = _make_namespace(
            action="buy", symbol="000001", quantity=500, price="12.50",
        )
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_trade(args, {"broker": {"active": "easytrader"}})
        mock_broker.buy.assert_called_once_with("000001", 500, Decimal("12.50"))

    def test_sell_calls_broker(self):
        """sell 操作调用 broker.sell。"""
        mock_broker = MagicMock()
        mock_broker.sell.return_value = OrderResult(
            order_id="S1", symbol="600036", side=OrderSide.SELL,
            quantity=200, price=Decimal("35.00"), status=OrderStatus.SUBMITTED,
        )
        args = _make_namespace(
            action="sell", symbol="600036", quantity=200, price="35.00",
        )
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_trade(args, {"broker": {"active": "easytrader"}})
        mock_broker.sell.assert_called_once_with("600036", 200, Decimal("35.00"))

    def test_invalid_price_exits(self):
        """无效价格退出。"""
        args = _make_namespace(
            action="buy", symbol="000001", quantity=500, price="abc",
        )
        with pytest.raises(SystemExit):
            _handle_trade(args, {})

    def test_zero_quantity_exits(self):
        """数量为零退出。"""
        args = _make_namespace(
            action="buy", symbol="000001", quantity=0, price="12.50",
        )
        with pytest.raises(SystemExit):
            _handle_trade(args, {})


class TestHandleCancel:
    """_handle_cancel 测试。"""

    def test_cancel_calls_broker(self):
        """cancel 操作调用 broker.cancel_order。"""
        mock_broker = MagicMock()
        mock_broker.cancel_order.return_value = True
        args = _make_namespace(order_id="ORD001")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_cancel(args, {"broker": {"active": "easytrader"}})
        mock_broker.cancel_order.assert_called_once_with("ORD001")


class TestHandleQuery:
    """_handle_query 测试。"""

    def _make_broker_with_positions(self, positions):
        """构造带持仓数据的 mock broker。"""
        mock_broker = MagicMock()
        mock_broker.get_positions.return_value = positions
        return mock_broker

    def test_query_positions(self, capsys):
        """查询持仓输出格式。"""
        pos = Position(
            symbol="000001", name="平安银行", quantity=1000,
            available_quantity=800, cost_price=Decimal("12.50"),
            current_price=Decimal("13.20"), market_value=Decimal("13200"),
            profit=Decimal("700"), profit_pct=Decimal("5.6"),
        )
        mock_broker = self._make_broker_with_positions([pos])
        args = _make_namespace(target="positions")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_query(args, {"broker": {"active": "easytrader"}})
        captured = capsys.readouterr()
        assert "000001" in captured.out
        assert "平安银行" in captured.out

    def test_query_positions_empty(self, capsys):
        """空持仓提示。"""
        mock_broker = self._make_broker_with_positions([])
        args = _make_namespace(target="positions")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_query(args, {"broker": {"active": "easytrader"}})
        captured = capsys.readouterr()
        assert "无" in captured.out or "空" in captured.out or "没有" in captured.out

    def test_query_account(self, capsys):
        """查询账户输出格式。"""
        acct = Account(
            total_asset=Decimal("100000"), available_cash=Decimal("50000"),
            market_value=Decimal("48000"), frozen_cash=Decimal("2000"),
        )
        mock_broker = MagicMock()
        mock_broker.get_account.return_value = acct
        args = _make_namespace(target="account")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_query(args, {"broker": {"active": "easytrader"}})
        captured = capsys.readouterr()
        assert "100000" in captured.out

    def test_query_orders(self, capsys):
        """查询委托输出格式。"""
        order = Order(
            order_id="ORD001", symbol="000001", side=OrderSide.BUY,
            quantity=500, price=Decimal("12.80"), filled_quantity=300,
            avg_price=Decimal("12.75"), status=OrderStatus.PARTIAL_FILLED,
        )
        mock_broker = MagicMock()
        mock_broker.get_today_orders.return_value = [order]
        args = _make_namespace(target="orders")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_query(args, {"broker": {"active": "easytrader"}})
        captured = capsys.readouterr()
        assert "ORD001" in captured.out

    def test_query_orders_empty(self, capsys):
        """空委托提示。"""
        mock_broker = MagicMock()
        mock_broker.get_today_orders.return_value = []
        args = _make_namespace(target="orders")
        with patch("runtime.cli.create_broker") as mock_factory:
            mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
            mock_factory.return_value.__exit__ = MagicMock(return_value=False)
            _handle_query(args, {"broker": {"active": "easytrader"}})
        captured = capsys.readouterr()
        assert "无" in captured.out or "空" in captured.out or "没有" in captured.out


class TestMain:
    """main 集成测试。"""

    @patch("runtime.cli._init")
    @patch("runtime.cli.create_broker")
    def test_main_buy_flow(self, mock_factory, mock_init):
        """端到端 buy 流程。"""
        from runtime.cli import main

        mock_init.return_value = {"broker": {"active": "easytrader"}}
        mock_broker = MagicMock()
        mock_broker.buy.return_value = OrderResult(
            order_id="B1", symbol="000001", side=OrderSide.BUY,
            quantity=500, price=Decimal("12.50"), status=OrderStatus.SUBMITTED,
        )
        mock_factory.return_value.__enter__ = MagicMock(return_value=mock_broker)
        mock_factory.return_value.__exit__ = MagicMock(return_value=False)

        with patch("sys.argv", [
            "quant", "trade", "buy",
            "--symbol", "000001", "--quantity", "500", "--price", "12.50",
        ]):
            main()
        mock_broker.buy.assert_called_once()

    @patch("runtime.cli._init")
    @patch("runtime.cli.create_broker")
    def test_main_quant_engine_error(self, mock_factory, mock_init, capsys):
        """QuantEngineError 被捕获并输出。"""
        from runtime.cli import main

        mock_init.return_value = {"broker": {"active": "easytrader"}}
        mock_factory.return_value.__enter__ = MagicMock(
            side_effect=QuantEngineError("测试错误"),
        )
        mock_factory.return_value.__exit__ = MagicMock(return_value=False)

        with patch("sys.argv", [
            "quant", "trade", "buy",
            "--symbol", "000001", "--quantity", "500", "--price", "12.50",
        ]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr()
        assert "测试错误" in captured.out or "测试错误" in captured.err
