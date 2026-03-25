# Polymarket Auto Redeemer

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](#环境要求)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#许可证)

用于 **自动扫描并领取已结算 Polymarket 头寸奖励** 的多账户自动化脚本。

该项目会定期扫描你的 Polymarket 头寸，并通过 Polymarket Relayer 工作流自动发起领取交易。支持多账户、批量领取、失败重试、代理设置以及日志落盘。

> 适合希望长期运行、自动处理已结算头寸领取流程的用户。

---

## 功能特性

- 自动扫描 `redeemable` / `mergeable` 的已结算头寸
- 自动调用 `redeemPositions` 批量领取
- 单个 JSON 配置文件支持多账户
- 支持 Safe / Relayer 交易流程
- 支持重试间隔控制，避免高频重复尝试
- 支持自定义扫描频率与单次最大处理数量
- 支持 HTTP / HTTPS 代理
- 关键日志写入 `redeem.log`
- 缺少配置文件时自动生成默认模板

---

## 工作原理

程序会循环执行以下步骤：

1. 从 Polymarket Data API 拉取头寸数据
2. 识别可领取或可合并的已结算头寸
3. 对 condition 进行去重
4. 仅筛选属于当前 `funder_address` 的可自动领取头寸
5. 构建批量 `redeemPositions` 交易
6. 通过配置好的 relayer 客户端发起执行
7. 将成功 / 失败结果输出到控制台和日志文件

---

## 环境要求

- Python 3.9+
- 可用的私钥
- 可用的 `funder_address` / 代理钱包 / Safe 地址
- Polymarket Builder 凭据：
  - `builder_api_key`
  - `builder_secret`
  - `builder_passphrase`

### Python 依赖

- `web3`
- `requests`
- `py-builder-relayer-client`
- `py-builder-signing-sdk`

---

## Linux 一行命令（下载 + 配置 + 运行）

Linux 用户可直接执行下面一行命令：自动完成仓库拉取/更新、虚拟环境创建、依赖安装、`config_redeem.json` 生成、打开编辑器配置并启动程序。

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Ibook000/polymarket-auto-redeemer/main/scripts/quickstart.sh)"
```

可选环境变量（覆盖默认值）：

```bash
INSTALL_DIR=$HOME/my-redeemer PYTHON_BIN=python3.11 EDITOR=vim bash -c "$(curl -fsSL https://raw.githubusercontent.com/Ibook000/polymarket-auto-redeemer/main/scripts/quickstart.sh)"
```

如果你希望先本地审阅脚本再执行：

```bash
bash scripts/quickstart.sh
```

---

## 一键启动 / 一键停止（小白友好）

完整图文教程：[`ONE_CLICK_GUIDE.zh-CN.md`](./ONE_CLICK_GUIDE.zh-CN.md)


给 0 基础用户，克隆仓库后直接执行：

```bash
bash scripts/edit_config.sh
bash scripts/one_click_start.sh
bash scripts/one_click_stop.sh
```

建议先编辑配置（非常重要）：
- 先执行 `bash scripts/edit_config.sh`

一键启动会自动完成：
- 不存在则创建 `.venv`
- 安装依赖
- 不存在则从模板生成 `config_redeem.json`
- 后台启动程序并将 PID 写入 `.redeemer.pid`
- 运行日志写入 `redeemer.runtime.log`

常用查看命令：

```bash
tail -f redeemer.runtime.log
cat .redeemer.pid
```

---

## 安装

克隆仓库：

```bash
git clone https://github.com/Ibook000/polymarket-auto-redeemer.git
cd polymarket-auto-redeemer
```

安装依赖：

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install web3 requests py-builder-relayer-client py-builder-signing-sdk
```

---

## 项目结构

```text
polymarket-auto-redeemer/
├── auto_redeem.py
├── main.py
├── redeemer.py
├── relayer_adapter.py
├── polymarket_client.py
├── config.py
├── config_redeem.example.json
├── requirements.txt
├── .gitignore
├── README.md
├── README.zh-CN.md
└── LICENSE
```

---

## 配置说明

脚本默认读取以下配置文件：

```text
config_redeem.json
```

如果文件不存在，程序会自动生成默认模板。

---

## 配置示例

```json
{
  "global": {
    "enabled": true,
    "scan_interval": 15,
    "retry_interval": 120,
    "max_per_scan": 10,
    "pending_log_interval": 10,
    "relayer_url": "https://relayer-v2.polymarket.com",
    "relayer_tx_type": "SAFE",
    "http_proxy": "",
    "https_proxy": ""
  },
  "accounts": [
    {
      "name": "account-1",
      "private_key": "0xYOUR_PRIVATE_KEY",
      "funder_address": "0xYOUR_FUNDER_ADDRESS",
      "builder_api_key": "YOUR_API_KEY",
      "builder_secret": "YOUR_API_SECRET",
      "builder_passphrase": "YOUR_API_PASSPHRASE",
      "enabled": true
    }
  ]
}
```

---

## 配置项说明

### 全局配置

| 字段 | 类型 | 说明 |
|---|---|---|
| `enabled` | bool | 全局启用或禁用自动领取 |
| `scan_interval` | int | 扫描间隔，单位秒 |
| `retry_interval` | int | 同一 condition 的最小重试间隔，单位秒 |
| `max_per_scan` | int | 每轮最多处理的 condition 数量 |
| `pending_log_interval` | int | 重复输出待领取状态日志的最小间隔 |
| `relayer_url` | string | Relayer 地址 |
| `relayer_tx_type` | string | Relayer 交易类型，默认 `SAFE` |
| `http_proxy` | string | 可选 HTTP 代理 |
| `https_proxy` | string | 可选 HTTPS 代理 |

### 账户配置

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 账户名，用于日志显示 |
| `private_key` | string | 签名私钥 |
| `funder_address` | string | Proxy / Safe / funder 地址 |
| `builder_api_key` | string | Builder API Key |
| `builder_secret` | string | Builder API Secret |
| `builder_passphrase` | string | Builder API Passphrase |
| `enabled` | bool | 是否启用该账户 |


### 账户类型 / Signature Type 对照

`funder_address` 必须和你的真实账户类型一致，否则会出现“能扫到仓位但无法领取”的问题。

| signature_type | Account Type | How You Signed Up |
|---:|---|---|
| `1` | Poly Proxy | Email or social login (Google, etc.) |
| `2` | Gnosis Safe | Browser wallet (MetaMask, Rainbow, Coinbase Wallet, etc.) |
| `0` | EOA | Direct on-chain interaction (no proxy) |

在本项目中的映射建议：

- `private_key`：用于签名的私钥。
- `funder_address`：真正持有可领取仓位的地址（Proxy / Safe / EOA 地址）。
- `global.relayer_tx_type`：
  - Safe 路径通常用 `SAFE`（对应 signature_type `2`）
  - Proxy 路径可用 `PROXY`（需 SDK/Relayer 支持，对应 signature_type `1`）
  - EOA（signature_type `0`）请先确认你的 relayer/sdk 是否支持再上生产。

启动前快速检查：

1. 配置里的 `funder_address` 与 Polymarket 页面展示地址完全一致。
2. `private_key` 与该账户类型实际签名人一致。
3. `relayer_tx_type` 与账户类型一致（Safe / Proxy）。

---

## 使用方式

运行脚本：

```bash
python auto_redeem.py
```

程序会依次完成：

- 校验依赖
- 加载配置
- 初始化有效账户
- 启动后台扫描线程
- 自动领取符合条件的头寸

停止方式：

```bash
Ctrl + C
```

---

## 日志说明

关键运行状态会输出到控制台。

以下级别日志也会写入 `redeem.log`：

- `OK`
- `ERR`
- `TRADE`

示例：

```text
2026-03-25 12:00:00 [OK] [account-1] Auto redeem started | scan interval: 15s | max per scan: 10
2026-03-25 12:00:15 [WARN] [account-1] | redeemable: 3 | auto-redeemable: 3 | address: 0x...
2026-03-25 12:00:16 [OK] [account-1] Successfully redeemed 3 conditions | 0x123...
```

---

## 多账户支持

本项目支持在同一个配置文件中管理多个账户。

只需在 `accounts` 数组下添加多个账户对象，程序会为每个启用的账户初始化一个独立的自动领取线程。

---

## 安全说明

这个仓库**绝对不要**提交真实敏感信息。

### 不要提交的内容

- 真实私钥
- 真实 Builder API 凭据
- 真实 `config_redeem.json`
- `redeem.log`
- 任何生产钱包或环境相关密钥

### 推荐做法

- 仓库只提交 `config_redeem.example.json`
- 真实 `config_redeem.json` 保留在本地并加入 Git 忽略
- 尽量使用专用自动化钱包而不是主钱包
- 先小规模测试后再正式运行
- 在使用真实资金前先审阅代码

---

## 风险声明

本项目会与区块链基础设施及第三方服务交互。

使用本软件的全部风险由使用者自行承担。作者**不对以下情况负责**：

- 资金损失
- 交易失败
- Relayer / API 服务异常
- 配置错误
- 密钥管理失误
- 任何非预期链上行为

请在使用真实资产前自行审查、测试并充分理解代码逻辑。

---

## 常见问题

### 缺少 `web3`

```bash
pip install web3
```

### 缺少 Builder SDK

```bash
pip install py-builder-relayer-client py-builder-signing-sdk
```

### 检测到可领取头寸但没有实际发起领取

常见原因：

- 该头寸不属于配置的 `funder_address`
- 尚未达到 `retry_interval`
- relayer 执行失败
- Builder 凭据无效
- Safe / proxy 钱包未正确部署或未配置完成

### 程序一直提示没有可领取头寸

通常说明当前扫描地址下没有同时满足以下条件的头寸：
- 已结算并且可领取 / 可合并
- 属于当前账户可自动处理的领取范围

---

## 开发计划

- [ ] 支持环境变量配置
- [ ] 支持 Docker
- [ ] 更完善的结构化日志
- [ ] 支持通知集成
- [ ] 支持 dry-run 模式
- [ ] 支持自定义配置路径的 CLI 参数

---

## 许可证

MIT License
