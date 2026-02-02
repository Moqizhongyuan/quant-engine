"""
账户管理命令

提供账户信息查看功能。
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="账户管理命令")
console = Console()


@app.command("info")
def account_info():
    """查看账户信息"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker

    broker = MiniQMTBroker()

    try:
        broker.connect()
        account = broker.get_account()

        table = Table(title="账户信息")
        table.add_column("项目", style="cyan")
        table.add_column("数值", justify="right")

        table.add_row("账户ID", account.account_id)
        table.add_row("总资产", f"{account.total_asset:,.2f}")
        table.add_row("可用资金", f"{account.cash:,.2f}")
        table.add_row("冻结资金", f"{account.frozen_cash:,.2f}")
        table.add_row("持仓市值", f"{account.market_value:,.2f}")
        table.add_row("仓位比例", f"{float(account.position_ratio)*100:.2f}%")

        if account.total_profit_loss >= 0:
            table.add_row("总盈亏", f"[green]+{account.total_profit_loss:,.2f}[/green]")
        else:
            table.add_row("总盈亏", f"[red]{account.total_profit_loss:,.2f}[/red]")

        if account.today_profit_loss >= 0:
            table.add_row("今日盈亏", f"[green]+{account.today_profit_loss:,.2f}[/green]")
        else:
            table.add_row("今日盈亏", f"[red]{account.today_profit_loss:,.2f}[/red]")

        console.print(table)

    except Exception as e:
        console.print(f"[red]获取账户信息失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("snapshot")
def save_snapshot():
    """保存账户快照"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.storage import init_database
    from quant_engine.storage.database import AccountSnapshotTable, get_database

    init_database()

    broker = MiniQMTBroker()

    try:
        broker.connect()
        account = broker.get_account()

        db = get_database()
        with db.session() as session:
            snapshot = AccountSnapshotTable(
                account_id=account.account_id,
                total_asset=float(account.total_asset),
                cash=float(account.cash),
                market_value=float(account.market_value),
                total_profit_loss=float(account.total_profit_loss),
            )
            session.add(snapshot)

        console.print("[green]账户快照已保存[/green]")

    except Exception as e:
        console.print(f"[red]保存快照失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()
