import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Debian package build tester (skeleton)"
    )

    parser.add_argument(
        "--csv",
        help="Path to CSV file containing repository URLs",
        required=False,
    )

    parser.add_argument(
        "--out",
        help="Output result file path",
        required=False,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("Program started")
    print(f"CSV path: {args.csv}")
    print(f"Output path: {args.out}")


if __name__ == "__main__":
    main()
