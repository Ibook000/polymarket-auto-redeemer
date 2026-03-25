# 一键启动/停止超详细教程（0基础）

> 适用于 Linux / WSL / 云服务器。

## 1) 安装基础工具

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv
```

## 2) 下载项目

```bash
git clone https://github.com/Ibook000/polymarket-auto-redeemer.git
cd polymarket-auto-redeemer
```

## 3) 一键编辑配置（必须）

```bash
bash scripts/edit_config.sh
```

打开后至少要改这几个字段：
- `private_key`
- `funder_address`
- `builder_api_key`
- `builder_secret`
- `builder_passphrase`

保存退出后继续下一步。

## 4) 一键启动

```bash
bash scripts/one_click_start.sh
```

启动成功后会看到：
- PID 文件：`.redeemer.pid`
- 运行日志：`redeemer.runtime.log`

## 5) 查看运行状态

```bash
cat .redeemer.pid
tail -f redeemer.runtime.log
```

## 6) 一键停止

```bash
bash scripts/one_click_stop.sh
```

---

## 常见问题

### Q1: 启动提示占位符错误
说明你的 `config_redeem.json` 还没填真实值。再次执行：

```bash
bash scripts/edit_config.sh
```

### Q2: 如何重启
先停再启：

```bash
bash scripts/one_click_stop.sh
bash scripts/one_click_start.sh
```

### Q3: 如何开机自启
建议后续使用 `systemd`（如你需要我可以直接给你现成 service 文件）。
