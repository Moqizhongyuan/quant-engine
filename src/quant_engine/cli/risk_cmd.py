"""
风控管理命令

提供风控检查、配置等功能。
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="风控管理命令")
console = Console()


@app.command("check")
def check_risk():
    """执行风控检查"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.risk import RiskManager
    from quant_engine.storage import init_database

    init_database()

    broker = MiniQMTBroker()
    risk_manager = RiskManager()

    try:
        broker.connect()
        account = broker.get_account()
        positions = broker.get_positions()

        results = risk_manager.check_all(account, positions)

        table = Table(title="风控检查结果")
        table.add_column("规则", style="cyan")
        table.add_column("状态")
        table.add_column("说明")

        passed_count = 0
        failed_count = 0

        for result in results:
            if result.passed:
                status = "[green]通过[/green]"
                passed_count += 1
            else:
                status = "[red]未通过[/red]"
                failed_count += 1

            table.add_row(result.rule, status, result.message)

        console.print(table)
        console.print(f"\n检查完成: [green]{passed_count} 通过[/green], [red]{failed_count} 未通过[/red]")

        if failed_count > 0:
            console.print("\n[yellow]建议: 请关注未通过的风控项目[/yellow]")

    except Exception as e:
        console.print(f"[red]风控检查失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()


@app.command("config")
def show_risk_config():
    """显示风控配置"""
    from quant_engine.utils.config import get_settings

    settings = get_settings()
    risk = settings.risk

    table = Table(title="风控配置")
    table.add_column("参数", style="cyan")
    table.add_column("值", justify="right")
    table.add_column("说明")

    table.add_row("enabled", str(risk.enabled), "是否启用风控")
    table.add_row("max_position_ratio", f"{risk.max_position_ratio*100:.0f}%", "单只股票最大持仓比例")
    table.add_row("max_daily_loss_ratio", f"{risk.max_daily_loss_ratio*100:.0f}%", "单日最大亏损比例")
    table.add_row("stop_loss_ratio", f"{risk.stop_loss_ratio*100:.0f}%", "止损比例")
    table.add_row("take_profit_ratio", f"{risk.take_profit_ratio*100:.0f}%", "止盈比例")
    table.add_row("max_holdings", str(risk.max_holdings), "最大持仓股票数量")
    table.add_row("max_order_amount", f"{risk.max_order_amount:,.0f}", "单笔最大交易金额")

    console.print(table)


@app.command("stop-loss")
def check_stop_loss():
    """检查止损触发情况"""
    from quant_engine.adapters.broker.miniqmt import MiniQMTBroker
    from quant_engine.core.risk import RiskManager
    from quant_engine.storage import init_database

    init_database()

    broker = MiniQMTBroker()
    risk_manager = RiskManager()

    try:
        broker.connect()
        positions = broker.get_positions()

        if not positions:
            console.print("[yellow]当前没有持仓[/yellow]")
            return

        triggered = []
        for position in positions:
            result = risk_manager._check_stop_loss(position)
            if not result.passed:
                triggered.append((position, result))

        if triggered:
            console.print(f"[red]发现 {len(triggered)} 只股票触发止损:[/red]")
            for position, result in triggered:
                console.print(f"  - {position.symbol}: {result.message}")
        else:
            console.print("[green]没有股票触发止损[/green]")

    except Exception as e:
        console.print(f"[red]检查失败: {e}[/red]")
        raise typer.Exit(1)
    finally:
        broker.disconnect()
