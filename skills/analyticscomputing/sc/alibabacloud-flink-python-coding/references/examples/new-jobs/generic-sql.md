# New Job Example: Generic SQL Connectors

Use this pattern for SQL connectors without dedicated DataFrame wrappers. It demonstrates the built-in `datagen` source and `blackhole` sink. Verify the target package API and connector documentation before adapting it.

## Complete `job.py`

```python
import pyflink.dataframe as pf


ROWS_PER_SECOND = 10


def main() -> None:
    orders = pf.read_generic(
        "datagen",
        schema={
            "order_id": pf.DataType.int64(),
            "customer_id": pf.DataType.int64(),
            "amount": pf.DataType.float64(),
        },
        options={
            "rows-per-second": str(ROWS_PER_SECOND),
            "fields.order_id.kind": "sequence",
            "fields.order_id.start": "1",
            "fields.order_id.end": "1000000",
            "fields.customer_id.min": "1",
            "fields.customer_id.max": "100000",
            "fields.amount.min": "-100.0",
            "fields.amount.max": "1000.0",
        },
    )

    valid_orders = orders.filter(pf.col("amount") > pf.lit(0.0)).select(
        "order_id",
        "customer_id",
        "amount",
    )

    valid_orders.write_generic("blackhole")


if __name__ == "__main__":
    main()
```

## Adaptation contract

- Replace `datagen` and its options only after the confirmed source factory and SQL DDL options select `read_generic`.
- Replace `blackhole` only after the confirmed sink factory and options select `write_generic`.
- Keep connector option names identical to their SQL DDL `WITH` keys.
- Add `primary_key=` only when the selected connector contract requires it.
- Let the DataFrame methods load registered built-in connector artifacts. Attach a JAR only for a confirmed custom or non-built-in factory.

This example selects no third-party Python package or runtime file. Syntax and artifact checks are local; connector discovery, planning, execution, and generated-row behavior are VVR-only.
