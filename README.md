# Polymarket Auto Redeemer

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](#requirements)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

Automated redemption bot for settled Polymarket positions.

This project periodically scans your Polymarket positions and automatically redeems rewards for settled conditions through the Polymarket relayer workflow. It supports multiple accounts, batched redemption, retry control, proxy configuration, and log persistence.

> Designed for users who want a lightweight, configurable, multi-account auto-redeem workflow for Polymarket.

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

This project supports multiple accounts in a single config file.

Add multiple account objects under the `accounts` array, and the script will initialize one redeemer thread for each enabled account.

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
