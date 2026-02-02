# Quant Engine - 量化交易平台

A股日频量化交易系统，支持从聚宽获取策略信号，通过 miniQMT 执行交易。

## 功能特性

- 多数据源支持（聚宽爬虫）
- miniQMT 交易接口集成
- 完整的风控体系（止损、止盈、仓位限制）
- CLI 命令行交互
- SQLite/PostgreSQL 数据存储

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd quant-engine

# 安装依赖
pip install -e .

# 或使用开发依赖
pip install -e ".[dev]"
```

### 配置

```bash
# 复制配置文件
cp config/settings.example.yaml config/settings.yaml
cp .env.example .env

# 编辑配置
vim config/settings.yaml
```

### 初始化数据库

```bash
quant-engine db init
```

### 基本使用

```bash
# 查看系统状态
quant-engine status

# 获取交易信号
quant-engine signal fetch

# 查看待执行信号
quant-engine signal list --pending

# 执行信号（模拟模式）
quant-engine signal execute --dry-run

# 查看持仓
quant-engine position list

# 查看账户
quant-engine account info

# 风控检查
quant-engine risk check
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `quant-engine status` | 显示系统状态 |
| `quant-engine signal fetch` | 获取交易信号 |
| `quant-engine signal list` | 查看信号列表 |
| `quant-engine signal execute` | 执行信号 |
| `quant-engine order list` | 查看订单列表 |
| `quant-engine order submit` | 提交订单 |
| `quant-engine order cancel` | 撤销订单 |
| `quant-engine position list` | 查看持仓 |
| `quant-engine account info` | 查看账户 |
| `quant-engine risk check` | 风控检查 |
| `quant-engine config show` | 显示配置 |
| `quant-engine db init` | 初始化数据库 |

## 项目结构

```
quant-engine/
├── config/                 # 配置文件
├── src/quant_engine/
│   ├── cli/               # CLI 命令
│   ├── core/              # 核心引擎
│   ├── adapters/          # 适配器层
│   ├── models/            # 数据模型
│   ├── storage/           # 数据存储
│   └── utils/             # 工具函数
└── tests/                 # 测试
```

## 开发

```bash
# 运行测试
pytest

# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 代码格式化
black src tests
ruff check src tests
```

## 风控规则

| 规则 | 默认值 | 说明 |
|------|--------|------|
| 单股最大持仓 | 20% | 单只股票最大持仓比例 |
| 单日最大亏损 | 5% | 单日最大亏损比例 |
| 止损线 | 8% | 个股止损比例 |
| 止盈线 | 20% | 个股止盈比例 |
| 最大持仓数 | 10 | 最大持仓股票数量 |
| 单笔最大金额 | 10万 | 单笔最大交易金额 |

## 发展路线

1. **阶段一**：聚宽爬虫获取策略结果 → miniQMT 执行交易
2. **阶段二**：本地获取数据 → 本地运行策略 → 执行交易
3. **阶段三**：策略优化 → 第三方回测验证 → 参数调优

## 许可证

MIT License
