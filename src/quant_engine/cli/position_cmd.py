"""
持仓管理命令

提供持仓查看、同步等功能。
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="持仓管理命令")
console = Console()


@app.command("list")
def list_positions():
    """查看当前持仓"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.storage import init_database

    init_database()

    broker = MiniQMTBroker()

    try:
        broker.connect()
        positions = broker.get_positions()

        if not positions:
            console.print("[yellow]当前没有持仓[/yellow]")
            return

        _display_positions(positions)

    except Exception as e:
        console.print(f"[red]获取持仓失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("sync")
def sync_positions():
    """同步持仓数据到本地"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import PositionRepository

    init_database()

    broker = MiniQMTBroker()
    repo = PositionRepository()

    try:
        broker.connect()
        positions = broker.get_positions()

        for position in positions:
            repo.save(position)

        console.print(f"[green]同步了 {len(positions)} 条持仓记录[/green]")

        if positions:
            _display_positions(positions)

    except Exception as e:
        console.print(f"[red]同步持仓失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("local")
def list_local_positions():
    """查看本地持仓记录"""
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import PositionRepository

    init_database()
    repo = PositionRepository()

    positions = repo.list_positions()

    if not positions:
        console.print("[yellow]本地没有持仓记录[/yellow]")
        return

    _display_positions(positions)


def _display_positions(positions):
    """显示持仓表格"""
    table = Table(title="持仓列表")
    table.add_column("股票代码", style="cyan")
    table.add_column("名称")
    table.add_column("持仓数量", justify="right")
    table.add_column("可用数量", justify="right")
    table.add_column("成本价", justify="right")
    table.add_column("现价", justify="right")
    table.add_column("市值", justify="right")
    table.add_column("盈亏", justify="right")
    table.add_column("盈亏比例", justify="right")

    total_market_value = 0
    total_profit_loss = 0

    for position in positions:
        profit_loss = float(position.profit_loss)
        profit_ratio = float(position.profit_loss_ratio) * 100

        if profit_loss >= 0:
            pl_style = "green"
            pl_text = f"+{profit_loss:.2f}"
            ratio_text = f"+{profit_ratio:.2f}%"
        else:
            pl_style = "red"
            pl_text = f"{profit_loss:.2f}"
            ratio_text = f"{profit_ratio:.2f}%"

        table.add_row(
            position.symbol,
            position.name or "-",
            str(position.quantity),
            str(position.available_quantity),
            f"{position.avg_cost:.2f}",
            f"{position.current_price:.2f}",
            f"{position.market_value:.2f}",
            f"[{pl_style}]{pl_text}[/{pl_style}]",
            f"[{pl_style}]{ratio_text}[/{pl_style}]",
        )

        total_market_value += float(position.market_value)
        total_profit_loss += profit_loss

    console.print(table)

    console.print(f"\n总市值: {total_market_value:.2f}")
    if total_profit_loss >= 0:
        console.print(f"总盈亏: [green]+{total_profit_loss:.2f}[/green]")
    else:
        console.print(f"总盈亏: [red]{total_profit_loss:.2f}[/red]")
