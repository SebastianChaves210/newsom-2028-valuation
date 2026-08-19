"""Command-line interface.

    newsom2028 collect   pull all data sources (append-only snapshots)
    newsom2028 model     re-run models/report/dashboard from latest snapshots
    newsom2028 run       collect + model (the full pipeline)
"""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="newsom2028")
    parser.add_argument("command", choices=["collect", "model", "run"])
    args = parser.parse_args(argv)

    from newsom2028 import pipeline

    if args.command == "collect":
        pipeline.collect_all()
    elif args.command == "model":
        record = pipeline.run_models()
        from newsom2028 import dashboard, report

        report.write(record)
        dashboard.build(record)
        _print_verdict(record)
    else:
        record = pipeline.full_run()
        _print_verdict(record)
    return 0


def _print_verdict(record: dict) -> None:
    for key, contract in record["contracts"].items():
        print(
            f"{contract['label']:<24} price {100 * contract['market_price']:5.1f}¢  "
            f"fair {100 * contract['fair_median']:5.1f}¢  "
            f"[{100 * contract['fair_p10']:.1f}–{100 * contract['fair_p90']:.1f}]  "
            f"→ {contract['verdict']}"
        )


if __name__ == "__main__":
    sys.exit(main())
