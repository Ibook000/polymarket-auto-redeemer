# Polymarket Auto Redeemer

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](#requirements)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

Automated redemption bot for settled Polymarket positions.

This project periodically scans your Polymarket positions and automatically redeems rewards for settled conditions through the Polymarket relayer workflow. It supports multiple accounts, batched redemption, retry control, proxy configuration, and log persistence.

> Designed for users who want a lightweight, configurable, multi-account auto-redeem workflow for Polymarket.

---

## Language

- English (this file)
- Chinese: [`README.zh-CN.md`](./README.zh-CN.md)

---

## Features

- Automatic scanning of redeemable / mergeable settled positions
- Automatic batched redemption via `redeemPositions`
- Multi-account support through a single JSON config
- Safe / relayer-based transaction workflow
- Retry interval control to avoid excessive repeated attempts
- Configurable scan interval and per-scan batch size
- Optional HTTP / HTTPS proxy support
- Local logging to `redeem.log`
- Auto-generates a default config template when missing

---

## How It Works

The bot runs in a loop and performs the following steps:

1. Fetches positions from the Polymarket Data API
2. Filters positions that are marked as redeemable or mergeable
3. Deduplicates conditions
4. Selects positions that belong to the configured `funder_address`
5. Builds batched `redeemPositions` transactions
6. Sends transactions through the configured relayer client
7. Records success / failure status to console and log file

---

## Requirements

- Python 3.9 or higher
- A valid private key
- A valid `funder_address` / proxy wallet / Safe address
- Polymarket Builder credentials:
  - `builder_api_key`
  - `builder_secret`
  - `builder_passphrase`

### Python packages

- `web3`
- `requests`
- `py-builder-relayer-client`
- `py-builder-signing-sdk`

---

## One-Line Linux Setup (Download + Configure + Run)

Use this command on Linux to clone/update the repo, create a virtual environment, install dependencies, create `config_redeem.json`, open it in your editor, and then start the bot:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Ibook000/polymarket-auto-redeemer/main/scripts/quickstart.sh)"
```

Optional environment overrides:

```bash
INSTALL_DIR=$HOME/my-redeemer PYTHON_BIN=python3.11 EDITOR=vim bash -c "$(curl -fsSL https://raw.githubusercontent.com/Ibook000/polymarket-auto-redeemer/main/scripts/quickstart.sh)"
```

If your system Python is missing `venv`, quickstart now exits early with a clear system-dependency error and (on Debian/Ubuntu) prints install hints such as:

```bash
sudo apt update && sudo apt install -y python3-venv
sudo apt update && sudo apt install -y python3.12-venv
```

For audited/local usage, you can also run:

```bash
bash scripts/quickstart.sh
```

---

## One-Click Start / Stop (Beginner Friendly)

Detailed Chinese guide: [`ONE_CLICK_GUIDE.zh-CN.md`](./ONE_CLICK_GUIDE.zh-CN.md)


For users with zero Linux background, use these two commands after cloning the repo:

```bash
bash scripts/edit_config.sh
bash scripts/one_click_start.sh
bash scripts/one_click_stop.sh
```

Global (absolute-path) command style, so you can run from any working directory:

```bash
bash "$HOME/polymarket-auto-redeemer/scripts/edit_config.sh"
bash "$HOME/polymarket-auto-redeemer/scripts/one_click_start.sh"
bash "$HOME/polymarket-auto-redeemer/scripts/one_click_stop.sh"
```

Global command style (recommended). Quickstart auto-installs this command to `~/.local/bin/polymarket-redeemer`:

```bash
polymarket-redeemer edit-config
polymarket-redeemer start
polymarket-redeemer stop
```

If needed, install/update it manually:

```bash
bash scripts/install_global_cmd.sh
```

Edit config first (important):
- run `bash scripts/edit_config.sh`

What start does automatically:
- creates `.venv` if missing
- checks `python -m venv` dependency before creating `.venv` and prints install hints when missing
- installs dependencies
- auto-creates `config_redeem.json` from template if missing
- runs the bot in background and writes PID to `.redeemer.pid`
- writes runtime logs to `redeemer.runtime.log`

Useful checks:

```bash
tail -f redeemer.runtime.log
cat .redeemer.pid
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/Ibook000/polymarket-auto-redeemer.git
cd polymarket-auto-redeemer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install web3 requests py-builder-relayer-client py-builder-signing-sdk
```

---

## Project Structure

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
└── LICENSE
```

---

## Configuration

The script uses the following config file by default:

```text
config_redeem.json
```

If the file does not exist, the script will automatically generate a default template.

---

## Example Configuration

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

## Configuration Reference

### Global Options

| Key | Type | Description |
|---|---|---|
| `enabled` | bool | Enable or disable the auto-redeemer globally |
| `scan_interval` | int | Scan interval in seconds |
| `retry_interval` | int | Minimum retry delay for the same condition in seconds |
| `max_per_scan` | int | Maximum number of conditions processed per scan |
| `pending_log_interval` | int | Minimum interval between repeated pending-state logs |
| `relayer_url` | string | Relayer endpoint |
| `relayer_tx_type` | string | Relayer transaction type, default is `SAFE` |
| `http_proxy` | string | Optional HTTP proxy |
| `https_proxy` | string | Optional HTTPS proxy |

### Account Options

| Key | Type | Description |
|---|---|---|
| `name` | string | Human-readable account name for logging |
| `private_key` | string | Private key used for signing |
| `funder_address` | string | Proxy / Safe / funder address |
| `builder_api_key` | string | Builder API key |
| `builder_secret` | string | Builder API secret |
| `builder_passphrase` | string | Builder API passphrase |
| `enabled` | bool | Enable or disable the account |


### Account Type / Signature Type Guide

`funder_address` must match your actual account type. If this is wrong, the bot may find positions but fail to redeem.

| signature_type | Account Type | How You Signed Up |
|---:|---|---|
| `1` | Poly Proxy | Email or social login (Google, etc.) |
| `2` | Gnosis Safe | Browser wallet (MetaMask, Rainbow, Coinbase Wallet, etc.) |
| `0` | EOA | Direct on-chain interaction (no proxy) |

How to map it in this project:

- `private_key`: signer private key used by the relayer client.
- `funder_address`: the address that actually owns the redeemable position (Proxy/Safe/EOA).
- `global.relayer_tx_type`:
  - use `SAFE` for Safe-based flow (signature_type `2`)
  - use `PROXY` for proxy-based flow when your relayer SDK supports it (signature_type `1`)
  - for EOA-like direct ownership (signature_type `0`), verify your relayer/sdk route before production.

Quick checks before running:

1. The `funder_address` in config is exactly the same address shown by Polymarket for your positions.
2. The private key controls the signer expected by your account type.
3. `relayer_tx_type` is aligned with your account type (Safe vs Proxy).

---

## Usage

Run the script:

```bash
python auto_redeem.py
```

The application will:

- validate dependencies
- load configuration
- initialize all valid accounts
- start background scanning threads
- automatically redeem eligible positions

Stop the process with:

```bash
Ctrl + C
```

---

## Logging

Important events are printed to the console.

The following log levels are also written to `redeem.log`:

- `OK`
- `ERR`
- `TRADE`

Example:

```text
2026-03-25 12:00:00 [OK] [account-1] Auto redeem started | scan interval: 15s | max per scan: 10
2026-03-25 12:00:15 [WARN] [account-1] | redeemable: 3 | auto-redeemable: 3 | address: 0x...
2026-03-25 12:00:16 [OK] [account-1] Successfully redeemed 3 conditions | 0x123...
```

---

## Multi-Account Support

This project supports multiple accounts in one `config_redeem.json` file.

Each enabled account gets its own background redeemer thread. This is useful when you manage multiple Safes/proxy wallets.

### Pattern A: One process, many accounts (recommended)

Use one config file and put all accounts into `accounts`:

```json
{
  "global": {
    "enabled": true,
    "scan_interval": 15,
    "retry_interval": 120,
    "max_per_scan": 10,
    "pending_log_interval": 10,
    "relayer_url": "https://relayer-v2.polymarket.com",
    "relayer_tx_type": "SAFE"
  },
  "accounts": [
    {
      "name": "main-safe",
      "private_key": "0x...",
      "funder_address": "0x...",
      "builder_api_key": "...",
      "builder_secret": "...",
      "builder_passphrase": "...",
      "enabled": true
    },
    {
      "name": "sub-safe-1",
      "private_key": "0x...",
      "funder_address": "0x...",
      "builder_api_key": "...",
      "builder_secret": "...",
      "builder_passphrase": "...",
      "enabled": true
    }
  ]
}
```

Run normally:

```bash
python auto_redeem.py
```

### Pattern B: Temporarily disable specific accounts

Set `enabled: false` on any account to skip it without removing credentials from the file.

### Pattern C: Separate environments (dev/staging/prod)

Maintain multiple config files outside Git (for example: `config_redeem.dev.json`, `config_redeem.prod.json`) and copy the one you need to `config_redeem.json` before startup.

### Operational tips for multi-account setups

- Use unique `name` values so logs are easy to trace.
- Start with smaller `max_per_scan` and gradually increase.
- Use separate API credentials per account when possible.
- Keep one dedicated automation wallet per strategy/risk bucket.

---

## Security Notes

This repository should **never** contain real secrets.

### Do NOT commit

- real private keys
- real builder API credentials
- real `config_redeem.json`
- `redeem.log`
- any wallet-specific or production secrets

### Recommended practice

- commit only `config_redeem.example.json`
- keep `config_redeem.json` local and ignored by Git
- use a dedicated automation wallet when possible
- test with a small setup before production use
- review the code before running with real funds

---

## Risk Disclaimer

This software interacts with blockchain infrastructure and third-party services.

Use it at your own risk. The author is **not responsible** for:

- financial loss
- transaction failures
- relayer / API outages
- misconfiguration
- key management issues
- any unintended on-chain behavior

You are responsible for reviewing, testing, and understanding the code before using it with real assets.

---

## Troubleshooting

### Missing `web3`

```bash
pip install web3
```

### Missing Builder SDK

```bash
pip install py-builder-relayer-client py-builder-signing-sdk
```

### Redeemable positions detected but nothing is redeemed

Possible reasons:

- the position does not belong to the configured `funder_address`
- the retry interval has not elapsed yet
- relayer execution failed
- builder credentials are invalid
- the Safe / proxy wallet is not deployed or not configured correctly

### The script keeps saying there are no redeemable positions

That usually means the scanned addresses currently do not have positions that are both:
- settled and redeemable / mergeable
- eligible for the current account’s automatic redemption flow

---

## Roadmap

- [ ] Environment variable support
- [ ] Docker support
- [ ] Better structured logging
- [ ] Optional notification integrations
- [ ] Dry-run mode
- [ ] CLI arguments for custom config paths

---

## License

MIT License
