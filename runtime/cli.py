"""CLI 命令行入口，使用 argparse 实现子命令。"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation

from common.config import load_settings
from common.exceptions import QuantEngineError
from common.logger import get_logger, setup_logging
from trading.factory import create_broker

logger = get_logger(__name__)


def _init() -> dict:
    """加载配置并初始化日志，返回配置字典。"""
    settings = load_settings()
    log_cfg = settings.get("logging", {})
    setup_logging(
        level=log_cfg.get("level", "INFO"),
        file_path=log_cfg.get("file_path"),
    )
    return settings


def _handle_trade(args: argparse.Namespace, settings: dict) -> None:
    """处理交易子命令（buy/sell）。"""
    symbol: str = args.symbol
    quantity: int = args.quantity
    try:
        price = Decimal(args.price)
    except (InvalidOperation, TypeError):
        print(f"错误: 无效的价格 '{args.price}'")
        sys.exit(1)

    if quantity <= 0:
        print("错误: 数量必须为正整数")
        sys.exit(1)
    if price <= 0:
        print("错误: 价格必须为正数")
        sys.exit(1)

    with create_broker(settings) as broker:
        if args.action == "buy":
            result = broker.buy(symbol, quantity, price)
        else:
            result = broker.sell(symbol, quantity, price)
        print(f"委托已提交 | 订单号: {result.order_id} | "
              f"{'买入' if args.action == 'buy' else '卖出'} "
              f"{symbol} {quantity}股 @ {price}")


def _handle_query(args: argparse.Namespace, settings: dict) -> None:
    """处理查询子命令（positions/account/orders）。"""
    with create_broker(settings) as broker:
        if args.target == "positions":
            positions = broker.get_positions()
            if not positions:
                print("当前无持仓")
                return
            print(f"{'代码':<8} {'名称':<8} {'数量':>6} {'可用':>6} "
                  f"{'成本价':>10} {'现价':>10} {'市值':>12} {'盈亏':>10} {'盈亏%':>8}")
            print("-" * 88)
            for p in positions:
                print(f"{p.symbol:<8} {p.name:<8} {p.quantity:>6} {p.available_quantity:>6} "
                      f"{p.cost_price:>10.3f} {p.current_price:>10.3f} "
                      f"{p.market_value:>12.2f} {p.profit:>10.2f} {p.profit_pct:>7.2f}%")

        elif args.target == "account":
            acct = broker.get_account()
            print(f"总资产:   {acct.total_asset:>14.2f}")
            print(f"可用资金: {acct.available_cash:>14.2f}")
            print(f"股票市值: {acct.market_value:>14.2f}")
            print(f"冻结资金: {acct.frozen_cash:>14.2f}")

        elif args.target == "orders":
            orders = broker.get_today_orders()
            if not orders:
                print("当日无委托")
                return
            print(f"{'订单号':<12} {'代码':<8} {'方向':<4} {'数量':>6} "
                  f"{'价格':>10} {'成交量':>6} {'均价':>10} {'状态':<10}")
            print("-" * 76)
            for o in orders:
                side_str = "买入" if o.side.value == "buy" else "卖出"
                print(f"{o.order_id:<12} {o.symbol:<8} {side_str:<4} {o.quantity:>6} "
                      f"{o.price:>10.3f} {o.filled_quantity:>6} "
                      f"{o.avg_price:>10.3f} {o.status.value:<10}")


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="quant-engine",
        description="A股量化交易引擎 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # trade 子命令
    trade_parser = subparsers.add_parser("trade", help="交易操作")
    trade_parser.add_argument("action", choices=["buy", "sell"], help="买入或卖出")
    trade_parser.add_argument("--symbol", required=True, help="股票代码，如 000001")
    trade_parser.add_argument("--quantity", type=int, required=True, help="委托数量")
    trade_parser.add_argument("--price", required=True, help="委托价格")

    # query 子命令
    query_parser = subparsers.add_parser("query", help="查询操作")
    query_parser.add_argument(
        "target", choices=["positions", "account", "orders"], help="查询目标"
    )

    return parser


def main() -> None:
    """CLI 主入口。"""
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = _init()

        if args.command == "trade":
            _handle_trade(args, settings)
        elif args.command == "query":
            _handle_query(args, settings)
    except QuantEngineError as e:
        logger.error("操作失败: %s", e)
        print(f"错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)


if __name__ == "__main__":
    main()
