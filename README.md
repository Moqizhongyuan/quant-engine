# Quant Engine

A 股量化交易平台，面向个体散户，提供统一的券商交易接口和 CLI 操作入口。

## 架构

采用**适配器模式 + 工厂模式**，通过配置文件切换底层券商实现：

```
Broker (ABC)
├── EasyTraderBroker   ← 当前可用，基于 easytrader 库
└── QMTBroker          ← 接口预留，待实现
```

核心接口：`connect` / `disconnect` / `buy` / `sell` / `cancel_order` / `get_positions` / `get_account` / `get_today_orders`

## 项目结构

```
quant-engine/
├── common/                 # 基建模块
│   ├── types.py            # 类型定义（枚举 + 数据类）
│   ├── exceptions.py       # 异常层次
│   ├── config.py           # YAML 配置加载，支持 ${ENV_VAR} 展开
│   └── logger.py           # 日志配置（控制台 + 文件轮转）
├── trading/                # 交易核心
│   ├── broker.py           # Broker 抽象基类
│   ├── easytrader_broker.py # EasyTrader 实现
│   ├── qmt_broker.py       # QMT 桩代码
│   └── factory.py          # 工厂函数 create_broker()
├── runtime/                # 运行时入口
│   ├── cli.py              # CLI 命令行（argparse）
│   └── __main__.py         # python -m runtime.cli 入口
├── data/                   # 数据模块（预留）
├── strategy/               # 策略模块（预留）
├── backtest/               # 回测模块（预留）
├── scripts/                # 脚本模块（预留）
├── config/
│   └── settings.yaml       # 运行时配置
└── pyproject.toml
```

## 环境要求

- Python >= 3.10
- 依赖：`easytrader >= 0.22`、`pyyaml >= 6.0`

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置环境变量

```bash
export BROKER_ACCOUNT="你的券商账号"
export BROKER_PASSWORD="你的券商密码"
```

### 3. 修改配置

编辑 `config/settings.yaml`，设置券商类型和参数：

```yaml
broker:
  active: easytrader          # 切换为 "qmt" 即可切换实现
  easytrader:
    broker_name: ht            # 券商：ht/yh/gj 等
    account: "${BROKER_ACCOUNT}"
    password: "${BROKER_PASSWORD}"
    exe_path: ""
```

### 4. 使用 CLI

```bash
# 买入
python -m runtime.cli trade buy --symbol 000001 --quantity 100 --price 10.50

# 卖出
python -m runtime.cli trade sell --symbol 000001 --quantity 100 --price 11.00

# 查询持仓
python -m runtime.cli query positions

# 查询账户资金
python -m runtime.cli query account

# 查询当日委托
python -m runtime.cli query orders
```

## 配置说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `broker.active` | 当前使用的券商适配器 | `easytrader` / `qmt` |
| `broker.easytrader.broker_name` | easytrader 券商标识 | `ht`（华泰）/ `yh`（银河）/ `gj`（国金） |
| `broker.easytrader.account` | 券商账号，支持环境变量 | `${BROKER_ACCOUNT}` |
| `broker.easytrader.password` | 券商密码，支持环境变量 | `${BROKER_PASSWORD}` |
| `broker.easytrader.exe_path` | 券商客户端路径（可选） | `C:/htzqv6/xiadan.exe` |
| `logging.level` | 日志级别 | `INFO` / `DEBUG` / `WARNING` |
| `logging.file_path` | 日志文件路径 | `logs/quant_engine.log` |

## 编程接口

除 CLI 外，也可在代码中直接使用：

```python
from common.config import load_settings
from trading.factory import create_broker

settings = load_settings()

with create_broker(settings) as broker:
    # 查询账户
    account = broker.get_account()
    print(f"可用资金: {account.available_cash}")

    # 查询持仓
    positions = broker.get_positions()

    # 下单（价格使用 Decimal）
    from decimal import Decimal
    result = broker.buy("000001", 100, Decimal("10.50"))
    print(f"订单号: {result.order_id}")
```

## 设计要点

- **价格精度**：所有价格字段使用 `Decimal`，避免浮点精度问题
- **敏感信息**：账号密码通过 `${ENV_VAR}` 从环境变量读取，不硬编码
- **连接管理**：Broker 支持 `with` 上下文管理器，自动 connect/disconnect
- **字段映射**：easytrader 返回的中文字段在 `EasyTraderBroker` 内部统一转换为标准数据类
