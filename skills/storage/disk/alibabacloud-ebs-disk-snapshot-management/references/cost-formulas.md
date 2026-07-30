# Snapshot Cost Formulas and Optimization

## Billing model

Alibaba Cloud bills snapshots per region based on snapshot capacity and usage duration. Billing starts when a snapshot is created and ends when it is deleted.

## Standard snapshot cost

```
Standard snapshot cost = Unit price × Snapshot capacity (GiB) × Billing duration
```

### Hourly equivalent

For pay-as-you-go standard snapshots billed by the hour:

```
Hourly cost = (Monthly unit price / 30 / 24) × Capacity (GiB)
```

### Example

Region: China East 1 (Hangzhou)
- Standard snapshot monthly price: 0.12 CNY/GiB/month
- Snapshot capacity: 50 GiB
- Billing duration: 2 months

```
Cost = 0.12 × 50 × 2 = 12 CNY
```

## Archive snapshot cost

```
Archive snapshot cost = Archive unit price × Archive capacity (GiB) × Archive duration
```

### Important notes

- Archive snapshots typically cost about 50% of standard snapshots.
- Minimum retention in archive tier: 60 days (1,440 hours).
- Early deletion before 60 days incurs an **archive early-deletion fee**.

### Archive early-deletion fee

```
Early-deletion fee = Standard unit price × Archived capacity × (1,440 - Actual archive hours) / 1,440
```

### Example

Region: China East 1 (Hangzhou)
- Standard price: 0.12 CNY/GiB/month
- Archive price: 0.06 CNY/GiB/month
- Capacity: 50 GiB
- Archived for 2 months

```
Archive cost = 0.06 × 50 × 2 = 6 CNY
```

## Cross-region copy cost

```
Copy traffic cost = Traffic unit price × Copied capacity (GiB)
Standard snapshot storage cost in target region = Target region price × Capacity × Duration
```

Archive snapshots cannot be copied across regions.

## Snapshot warm-up cost

Snapshot warm-up is charged based on the warmed capacity:

```
Warm-up cost = Warm-up unit price × Warmed capacity (GiB)
```

## Billing cycle

- Billing granularity: per hour, rounded up.
- Billing starts at the hour the snapshot is created.
- Billing ends at the hour the snapshot is deleted.

## Cost optimization recommendations

### 1. Reduce snapshot count

- Delete snapshots that are no longer needed.
- Use `scripts/snapshot_cleanup_planner.py` to identify candidates.

### 2. Adjust retention days

- Core applications: retain 1–2 snapshots per day for months.
- Non-core applications: retain weekly snapshots for days or weeks.
- Pre-upgrade snapshots: delete immediately after the change is verified.

### 3. Archive low-frequency snapshots

- Move long-retention, rarely accessed standard snapshots to archive tier.
- Ensure retention will exceed 60 days to avoid early-deletion fees.

### 4. Disable unused cross-region copy

- Stop cross-region copy for snapshots that do not need disaster recovery in another region.

### 5. Use resource packages

- Purchase OSS standard-LRS storage packages to offset standard snapshot storage fees.
- Purchase Storage Capacity Units (SCU) where applicable.

### 6. Clean up automatic snapshots

- Delete unused auto snapshot policies.
- Enable "delete automatic snapshots with disk" for ephemeral environments.

## Price disclaimer

Prices in examples are illustrative. Always refer to the [Alibaba Cloud ECS pricing page](https://www.aliyun.com/price/detail) for current rates. Use `--price-standard` and `--price-archive` in the cost calculator to override defaults.
