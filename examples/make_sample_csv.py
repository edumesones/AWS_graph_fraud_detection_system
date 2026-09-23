from __future__ import annotations

from pathlib import Path

from data.synthetic_generator import generate_transactions


def main() -> None:
    df = generate_transactions(seed=42, num_transactions=100)
    out = Path(__file__).resolve().parents[1] / "data" / "sample_data" / "transactions_sample.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"WROTE:{out} ROWS:{len(df)}")


if __name__ == "__main__":
    main()
