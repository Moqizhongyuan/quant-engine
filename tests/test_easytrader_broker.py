"""EasyTraderBroker 全部方法测试。"""

from __future__ import annotations

import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from common.exceptions import BrokerConnectionError, OrderCancelError, OrderSubmitError
from common.types import OrderSide, OrderStatus


class TestToDecimal:
    """_to_decimal 辅助函数测试。"""

    def _call(self, value):
        """调用 _to_decimal。"""
        from trading.easytrader_broker import _to_decimal
        return _to_decimal(value)

    def test_int_input(self):
        """整数输入正常转换。"""
        assert self._call(100) == Decimal("100")

    def test_float_input(self):
        """浮点数输入正常转换。"""
        result = self._call(12.5)
        assert result == Decimal("12.5")

    def test_string_input(self):
        """字符串输入正常转换。"""
        assert self._call("99.99") == Decimal("99.99")

    def test_invalid_string(self):
        """无效字符串返回 Decimal(0)。"""
        assert self._call("abc") == Decimal("0")

    def test_none_input(self):
        """None 输入返回 Decimal(0)。"""
        assert self._call(None) == Decimal("0")


class TestConnect:
    """connect 方法测试。"""

    def test_connect_success(self, mock_easytrader_module, mock_client):
        """正常连接成功。"""
        mock_easytrader_module.use.return_value = mock_client
        from trading.easytrader_broker import EasyTraderBroker

        broker = EasyTraderBroker("ht", "acc", "pwd")
        broker.connect()

        mock_easytrader_module.use.assert_called_once_with("ht")
        mock_client.prepare.assert_called_once_with(
            user="acc", password="pwd"
        )
        assert broker._client is mock_client

    def test_connect_with_exe_path(self, mock_easytrader_module, mock_client):
        """带 exe_path 参数连接。"""
        mock_easytrader_module.use.return_value = mock_client
        from trading.easytrader_broker import EasyTraderBroker

        broker = EasyTraderBroker("ht", "acc", "pwd", exe_path="/path/to/exe")
        broker.connect()

        mock_client.prepare.assert_called_once_with(
            user="acc", password="pwd", exe_path="/path/to/exe"
        )

    def test_connect_failure(self, mock_easytrader_module):
        """连接失败抛出 BrokerConnectionError。"""
        mock_easytrader_module.use.side_effect = RuntimeError("连接超时")
        from trading.easytrader_broker import EasyTraderBroker

        broker = EasyTraderBroker("ht", "acc", "pwd")
        with pytest.raises(BrokerConnectionError, match="连接券商失败"):
            broker.connect()


class TestDisconnect:
    """disconnect 方法测试。"""

    def test_disconnect_clears_client(self, connected_broker):
        """断开连接后 client 为 None。"""
        assert connected_broker._client is not None
        connected_broker.disconnect()
        assert connected_broker._client is None


class TestContextManager:
    """上下文管理器测试。"""

    def test_context_manager(self, mock_easytrader_module, mock_client):
        """with 语句自动 connect/disconnect。"""
        mock_easytrader_module.use.return_value = mock_client
        from trading.easytrader_broker import EasyTraderBroker

        broker = EasyTraderBroker("ht", "acc", "pwd")
        with broker:
            assert broker._client is not None
        assert broker._client is None


class TestEnsureConnected:
    """_ensure_connected 方法测试。"""

    def test_not_connected_raises(self):
        """未连接时抛出 BrokerConnectionError。"""
        mock_module = MagicMock()
        with patch.dict(sys.modules, {"easytrader": mock_module}):
            from trading.easytrader_broker import EasyTraderBroker

            broker = EasyTraderBroker("ht", "acc", "pwd")
            with pytest.raises(BrokerConnectionError, match="未连接到券商"):
                broker._ensure_connected()


class TestBuy:
    """buy 方法测试。"""

    def test_buy_success(self, connected_broker, mock_client):
        """正常买入返回 OrderResult。"""
        mock_client.buy.return_value = {"entrust_no": "B100"}
        result = connected_broker.buy("000001", 500, Decimal("12.50"))

        mock_client.buy.assert_called_once_with(
            "000001", price=12.5, amount=500
        )
        assert result.order_id == "B100"
        assert result.side == OrderSide.BUY
        assert result.symbol == "000001"
        assert result.quantity == 500
        assert result.price == Decimal("12.50")

    def test_buy_failure(self, connected_broker, mock_client):
        """买入失败抛出 OrderSubmitError。"""
        mock_client.buy.side_effect = RuntimeError("资金不足")
        with pytest.raises(OrderSubmitError, match="买入委托失败"):
            connected_broker.buy("000001", 500, Decimal("12.50"))


class TestSell:
    """sell 方法测试。"""

    def test_sell_success(self, connected_broker, mock_client):
        """正常卖出返回 OrderResult。"""
        mock_client.sell.return_value = {"entrust_no": "S200"}
        result = connected_broker.sell("600036", 200, Decimal("35.00"))

        mock_client.sell.assert_called_once_with(
            "600036", price=35.0, amount=200
        )
        assert result.order_id == "S200"
        assert result.side == OrderSide.SELL

    def test_sell_failure(self, connected_broker, mock_client):
        """卖出失败抛出 OrderSubmitError。"""
        mock_client.sell.side_effect = RuntimeError("持仓不足")
        with pytest.raises(OrderSubmitError, match="卖出委托失败"):
            connected_broker.sell("600036", 200, Decimal("35.00"))


class TestCancelOrder:
    """cancel_order 方法测试。"""

    def test_cancel_success(self, connected_broker, mock_client):
        """正常撤单返回 True。"""
        result = connected_broker.cancel_order("ORD001")
        mock_client.cancel_entrust.assert_called_once_with("ORD001")
        assert result is True

    def test_cancel_failure(self, connected_broker, mock_client):
        """撤单失败抛出 OrderCancelError。"""
        mock_client.cancel_entrust.side_effect = RuntimeError("订单已成交")
        with pytest.raises(OrderCancelError, match="撤单失败"):
            connected_broker.cancel_order("ORD001")


class TestGetPositions:
    """get_positions 方法测试。"""

    def test_positions_mapping(
        self, connected_broker, mock_client, sample_chinese_position
    ):
        """正常映射持仓数据。"""
        mock_client.position = sample_chinese_position
        positions = connected_broker.get_positions()

        assert len(positions) == 1
        pos = positions[0]
        assert pos.symbol == "000001"
        assert pos.name == "平安银行"
        assert pos.quantity == 1000
        assert pos.available_quantity == 800
        assert pos.cost_price == Decimal("12.5")
        assert pos.current_price == Decimal("13.2")
        assert pos.market_value == Decimal("13200")
        assert pos.profit == Decimal("700")
        assert pos.profit_pct == Decimal("5.6")

    def test_positions_empty(self, connected_broker, mock_client):
        """空持仓返回空列表。"""
        mock_client.position = []
        positions = connected_broker.get_positions()
        assert positions == []


class TestGetAccount:
    """get_account 方法测试。"""

    def test_account_mapping(
        self, connected_broker, mock_client, sample_chinese_balance
    ):
        """正常映射资金数据。"""
        mock_client.balance = sample_chinese_balance
        account = connected_broker.get_account()

        assert account.total_asset == Decimal("100000")
        assert account.available_cash == Decimal("50000")
        assert account.market_value == Decimal("48000")
        assert account.frozen_cash == Decimal("2000")


class TestGetTodayOrders:
    """get_today_orders 方法测试。"""

    def test_orders_mapping(
        self, connected_broker, mock_client, sample_chinese_orders
    ):
        """正常映射委托数据。"""
        mock_client.today_entrusts = sample_chinese_orders
        orders = connected_broker.get_today_orders()

        assert len(orders) == 2

        # 第一条：买入，部成
        o1 = orders[0]
        assert o1.order_id == "ORD001"
        assert o1.symbol == "000001"
        assert o1.side == OrderSide.BUY
        assert o1.quantity == 500
        assert o1.price == Decimal("12.8")
        assert o1.filled_quantity == 300
        assert o1.avg_price == Decimal("12.75")
        assert o1.status == OrderStatus.PARTIAL_FILLED

        # 第二条：卖出，已成
        o2 = orders[1]
        assert o2.order_id == "ORD002"
        assert o2.symbol == "600036"
        assert o2.side == OrderSide.SELL
        assert o2.quantity == 200
        assert o2.status == OrderStatus.FILLED

    def test_unknown_status_defaults_to_pending(
        self, connected_broker, mock_client
    ):
        """未知状态默认映射为 PENDING。"""
        mock_client.today_entrusts = [
            {
                "合同编号": "ORD999",
                "证券代码": "000001",
                "操作": "买入",
                "委托数量": 100,
                "委托价格": 10.0,
                "成交数量": 0,
                "成交均价": 0,
                "备注": "未知状态",
            },
        ]
        orders = connected_broker.get_today_orders()
        assert orders[0].status == OrderStatus.PENDING

    def test_orders_empty(self, connected_broker, mock_client):
        """空委托返回空列表。"""
        mock_client.today_entrusts = []
        orders = connected_broker.get_today_orders()
        assert orders == []


class TestStatusMap:
    """_STATUS_MAP 全部状态值验证。"""

    def test_all_status_mappings(self):
        """验证全部 6 个状态映射。"""
        from trading.easytrader_broker import _STATUS_MAP

        expected = {
            "已报": OrderStatus.SUBMITTED,
            "已成": OrderStatus.FILLED,
            "部成": OrderStatus.PARTIAL_FILLED,
            "已撤": OrderStatus.CANCELLED,
            "废单": OrderStatus.REJECTED,
            "未报": OrderStatus.PENDING,
        }
        assert _STATUS_MAP == expected

    def test_status_map_length(self):
        """状态映射包含 6 个条目。"""
        from trading.easytrader_broker import _STATUS_MAP

        assert len(_STATUS_MAP) == 6
