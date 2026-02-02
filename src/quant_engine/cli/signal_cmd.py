"""
信号管理命令

提供信号获取、查看、执行等功能。
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="信号管理命令")
console = Console()


@app.command("fetch")
def fetch_signals(
    source: str = typer.Option("joinquant", "--source", "-s", help="数据源"),
):
    """从数据源获取交易信号"""
    from quant_engine.adapters.data.joinquant import JoinQuantCrawler
    from quant_engine.core.signal import SignalProcessor
    from quant_engine.storage import init_database

    init_database()

    console.print(f"正在从 {source} 获取信号...")

    try:
        if source == "joinquant":
            provider = JoinQuantCrawler()
        else:
            console.print(f"[red]不支持的数据源: {source}[/red]")
            raise typer.Exit(1)

        processor = SignalProcessor(provider)
        signals = processor.fetch_signals()

        if signals:
            console.print(f"[green]成功获取 {len(signals)} 个信号[/green]")
            _display_signals(signals)
        else:
            console.print("[yellow]未获取到新信号[/yellow]")

    except Exception as e:
        console.print(f"[red]获取信号失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_signals(
    pending: bool = typer.Option(False, "--pending", "-p", help="只显示待执行信号"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="按来源筛选"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示数量"),
):
    """查看交易信号列表"""
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import SignalRepository

    init_database()
    repo = SignalRepository()

    if pending:
        signals = repo.get_pending_signals()
    else:
        signals = repo.list_signals(source=source, limit=limit)

    if not signals:
        console.print("[yellow]没有找到信号[/yellow]")
        return

    _display_signals(signals)


@app.command("execute")
def execute_signals(
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="模拟执行，不实际下单"),
    signal_id: Optional[str] = typer.Option(None, "--id", help="指定信号ID"),
):
    """执行待处理的交易信号"""
    from uuid import UUID
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.executor import OrderExecutor
    from quant_engine.core.risk import RiskManager
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import SignalRepository

    init_database()

    broker = MiniQMTBroker(simulation=True if dry_run else None)
    risk_manager = RiskManager()
    executor = OrderExecutor(broker, risk_manager)
    signal_repo = SignalRepository()

    try:
        broker.connect()

        if signal_id:
            signals = [signal_repo.get_by_id(UUID(signal_id))]
            signals = [s for s in signals if s is not None]
        else:
            signals = signal_repo.get_pending_signals()

        if not signals:
            console.print("[yellow]没有待执行的信号[/yellow]")
            return

        console.print(f"准备执行 {len(signals)} 个信号...")

        if dry_run:
            console.print("[yellow]模拟模式：不会实际下单[/yellow]")

        account = broker.get_account()
        positions = broker.get_positions()

        for signal in signals:
            try:
                order = executor.execute_signal(signal, account, positions)
                console.print(
                    f"[green]信号已执行: {signal.symbol} {signal.direction.value} "
                    f"{signal.target_quantity}股 -> 订单 {order.id}[/green]"
                )
            except Exception as e:
                console.print(f"[red]信号执行失败 {signal.symbol}: {e}[/red]")

    except Exception as e:
        console.print(f"[red]执行失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


def _display_signals(signals):
    """显示信号表格"""
    table = Table(title="交易信号")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("股票代码", style="cyan")
    table.add_column("方向", style="green")
    table.add_column("目标数量", justify="right")
    table.add_column("目标价格", justify="right")
    table.add_column("来源", style="blue")
    table.add_column("已执行", style="yellow")
    table.add_column("创建时间")

    for signal in signals:
        direction_style = "green" if signal.direction.value == "BUY" else "red"
        table.add_row(
            str(signal.id)[:8],
            signal.symbol,
            f"[{direction_style}]{signal.direction.value}[/{direction_style}]",
            str(signal.target_quantity),
            f"{signal.target_price:.2f}" if signal.target_price else "-",
            signal.source,
            "是" if signal.executed else "否",
            signal.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
