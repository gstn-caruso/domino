#!/usr/bin/env python3
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Resuelve el plan de publicación de Dominó.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--run-number", required=True, type=int)
    args = parser.parse_args()

    if not 1 <= args.run_number <= 2_100_000_000:
        parser.error("--run-number debe ser un entero entre 1 y 2100000000, compatible con Android")

    version = f"0.1.{args.run_number}"
    print(json.dumps({
        "version": version,
        "tag": f"v{version}",
        "publish": args.event == "push" and args.ref == "refs/heads/main",
        "apk": f"domino-{version}.apk",
        "deb": f"domino_{version}_amd64.deb",
    }))


if __name__ == "__main__":
    main()
