"""
数据库管理命令

提供数据库初始化、迁移等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(help="数据库管理命令")
console = Console()


@app.command("init")
def init_database(
    force: bool = typer.Option(False, "--force", "-f", help="强制重建（删除现有数据）"),
):
    """初始化数据库"""
    from quant_engine.storage.database import Database, get_database
    from quant_engine.utils.config import get_settings

    settings = get_settings()

    if force:
        confirm = typer.confirm("确定要删除现有数据并重建数据库吗？")
        if not confirm:
            console.print("[yellow]操作已取消[/yellow]")
            raise typer.Exit(0)

    try:
        db = Database()

        if force:
            db.drop_tables()
            console.print("[yellow]已删除现有表[/yellow]")

        db.create_tables()
        console.print("[green]数据库初始化完成[/green]")
        console.print(f"数据库路径: {settings.database.url}")

    except Exception as e:
        console.print(f"[red]初始化失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def database_status():
    """查看数据库状态"""
    from sqlalchemy import inspect
    from quant_engine.storage.database import Database
    from quant_engine.utils.config import get_settings
    from rich.table import Table

    settings = get_settings()

    try:
        db = Database()
        inspector = inspect(db._engine)
        tables = inspector.get_table_names()

        console.print(f"数据库: {settings.database.url}")
        console.print(f"表数量: {len(tables)}")

        if tables:
            table = Table(title="数据库表")
            table.add_column("表名", style="cyan")
            table.add_column("列数", justify="right")

            for table_name in tables:
                columns = inspector.get_columns(table_name)
                table.add_row(table_name, str(len(columns)))

            console.print(table)
        else:
            console.print("[yellow]数据库中没有表，请运行 db init[/yellow]")

    except Exception as e:
        console.print(f"[red]获取状态失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("stats")
def database_stats():
    """查看数据统计"""
    from quant_engine.storage import init_database
    from quant_engine.storage.repository import (
        OrderRepository,
        PositionRepository,
        SignalRepository,
    )
    from rich.table import Table

    init_database()

    order_repo = OrderRepository()
    position_repo = PositionRepository()
    signal_repo = SignalRepository()

    try:
        orders = order_repo.list_orders(limit=10000)
        positions = position_repo.list_positions()
        signals = signal_repo.list_signals(limit=10000)

        table = Table(title="数据统计")
        table.add_column("数据类型", style="cyan")
        table.add_column("总数", justify="right")
        table.add_column("说明")

        table.add_row("订单", str(len(orders)), "所有订单记录")
        table.add_row("持仓", str(len(positions)), "当前持仓股票")
        table.add_row("信号", str(len(signals)), "交易信号记录")

        pending_signals = len([s for s in signals if not s.executed])
        table.add_row("待执行信号", str(pending_signals), "未执行的信号")

        active_orders = len([o for o in orders if not o.is_completed])
        table.add_row("活跃订单", str(active_orders), "未完成的订单")

        console.print(table)

    except Exception as e:
        console.print(f"[red]获取统计失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("clean")
def clean_database(
    days: int = typer.Option(30, "--days", "-d", help="保留最近N天的数据"),
):
    """清理历史数据"""
    console.print(f"[yellow]将清理 {days} 天前的历史数据[/yellow]")

    confirm = typer.confirm("确定要继续吗？")
    if not confirm:
        console.print("[yellow]操作已取消[/yellow]")
        raise typer.Exit(0)

    console.print("[yellow]功能开发中...[/yellow]")
