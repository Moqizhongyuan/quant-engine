"""
订单管理命令

提供订单查看、提交、撤销等功能。
"""

from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="订单管理命令")
console = Console()


@app.command("list")
def list_orders(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="按股票代码筛选"),
    status: Optional[str] = typer.Option(None, "--status", help="按状态筛选"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示数量"),
):
    """查看订单列表"""
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import OrderRepository

    init_database()
    repo = OrderRepository()

    orders = repo.list_orders(symbol=symbol, limit=limit)

    if status:
        orders = [o for o in orders if o.status.value == status.upper()]

    if not orders:
        console.print("[yellow]没有找到订单[/yellow]")
        return

    _display_orders(orders)


@app.command("submit")
def submit_order(
    symbol: str = typer.Argument(..., help="股票代码"),
    direction: str = typer.Argument(..., help="方向 (BUY/SELL)"),
    quantity: int = typer.Argument(..., help="数量"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="价格（不指定则市价）"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="模拟执行"),
):
    """提交新订单"""
    from decimal import Decimal
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.executor import OrderExecutor
    from quant_engine.core.risk import RiskManager
    from quant_engine.models.order import Order, OrderDirection, OrderType
    from quant_engine.storage import init_database

    init_database()

    try:
        order_direction = OrderDirection(direction.upper())
    except ValueError:
        console.print(f"[red]无效的方向: {direction}，请使用 BUY 或 SELL[/red]")
        raise typer.Exit(1)

    order = Order(
        symbol=symbol,
        direction=order_direction,
        quantity=quantity,
        price=Decimal(str(price)) if price else None,
        order_type=OrderType.LIMIT if price else OrderType.MARKET,
    )

    broker = MiniQMTBroker(simulation=True if dry_run else None)
    risk_manager = RiskManager()
    executor = OrderExecutor(broker, risk_manager)

    try:
        broker.connect()

        account = broker.get_account()
        positions = broker.get_positions()

        risk_result = risk_manager.check_order(order, account, positions)
        if not risk_result.passed:
            console.print(f"[red]风控检查未通过: {risk_result.message}[/red]")
            raise typer.Exit(1)

        if dry_run:
            console.print("[yellow]模拟模式：不会实际下单[/yellow]")

        order = executor.submit_order(order)
        console.print(f"[green]订单已提交: {order.id}[/green]")
        console.print(f"  股票: {order.symbol}")
        console.print(f"  方向: {order.direction.value}")
        console.print(f"  数量: {order.quantity}")
        console.print(f"  价格: {order.price or '市价'}")
        console.print(f"  状态: {order.status.value}")

    except Exception as e:
        console.print(f"[red]订单提交失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("cancel")
def cancel_order(
    order_id: str = typer.Argument(..., help="订单ID"),
):
    """撤销订单"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.executor import OrderExecutor
    from quant_engine.storage import init_database

    init_database()

    broker = MiniQMTBroker()
    executor = OrderExecutor(broker)

    try:
        broker.connect()
        success = executor.cancel_order(UUID(order_id))

        if success:
            console.print(f"[green]订单已撤销: {order_id}[/green]")
        else:
            console.print(f"[red]撤单失败: {order_id}[/red]")

    except Exception as e:
        console.print(f"[red]撤单失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("sync")
def sync_orders():
    """同步订单状态"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.executor import OrderExecutor
    from quant_engine.storage import init_database

    init_database()

    broker = MiniQMTBroker()
    executor = OrderExecutor(broker)

    try:
        broker.connect()
        orders = executor.sync_all_active_orders()

        if orders:
            console.print(f"[green]同步了 {len(orders)} 个订单[/green]")
            _display_orders(orders)
        else:
            console.print("[yellow]没有活跃订单需要同步[/yellow]")

    except Exception as e:
        console.print(f"[red]同步失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


def _display_orders(orders):
    """显示订单表格"""
    table = Table(title="订单列表")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("股票代码", style="cyan")
    table.add_column("方向")
    table.add_column("数量", justify="right")
    table.add_column("价格", justify="right")
    table.add_column("成交", justify="right")
    table.add_column("状态")
    table.add_column("创建时间")

    status_colors = {
        "PENDING": "yellow",
        "SUBMITTED": "blue",
        "PARTIAL_FILLED": "cyan",
        "FILLED": "green",
        "CANCELLED": "dim",
        "REJECTED": "red",
        "FAILED": "red",
    }

    for order in orders:
        direction_style = "green" if order.direction.value == "BUY" else "red"
        status_color = status_colors.get(order.status.value, "white")

        table.add_row(
            str(order.id)[:8],
            order.symbol,
            f"[{direction_style}]{order.direction.value}[/{direction_style}]",
            str(order.quantity),
            f"{order.price:.2f}" if order.price else "市价",
            f"{order.filled_quantity}/{order.quantity}",
            f"[{status_color}]{order.status.value}[/{status_color}]",
            order.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
