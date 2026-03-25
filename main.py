import sys
import time

from config import CONFIG_JSON_PATH
from redeemer import AutoRedeemer, HAS_BUILDER, HAS_WEB3, bootstrap_config_if_missing, log


def main():
    print("Polymarket Auto Redeemer")

    if not HAS_WEB3:
        log("Missing web3 dependency, exiting", "ERR")
        sys.exit(1)

    if not HAS_BUILDER:
        log("Missing Builder SDK dependency, exiting", "ERR")
        sys.exit(1)

    if bootstrap_config_if_missing(CONFIG_JSON_PATH):
        log(f"Config not found: {CONFIG_JSON_PATH}", "WARN")
        log("Created default config, please edit the config file and rerun the program", "WARN")
        sys.exit(0)

    redeemer = AutoRedeemer(CONFIG_JSON_PATH)

    if not redeemer.enabled:
        log("Auto redeem not enabled, exiting", "WARN")
        sys.exit(0)

    if not redeemer.account_redeemers:
        log("No valid accounts, exiting", "WARN")
        sys.exit(0)

    redeemer.start()

    log("Press Ctrl+C to stop", "INFO")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        log("Stop signal received...", "WARN")
        redeemer.stop()
        log("Program exited", "OK")


if __name__ == "__main__":
    main()
