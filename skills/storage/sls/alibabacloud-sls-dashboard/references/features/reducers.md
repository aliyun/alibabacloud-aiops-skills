# Reduction functions

Use when a chart must turn a returned field or series into one value.
Chart reductions operate on returned samples; query limits therefore affect the result.

| Value | Meaning |
| --- | --- |
| first / last | First / last sample, including null values. |
| firstNotNull / lastNotNull | First / last non-null sample. |
| min / max | Minimum / maximum value. |
| mean | Arithmetic mean. |
| total | Sum of samples; not a counter increase. |
| count | Sample count. |
| range | Maximum minus minimum. |
| difference | Last value minus first value. |
| differencePercent | Relative change between first and last values. |
| distinctCount | Number of distinct values. |
| minAboveZero | Smallest strictly positive value. |
| step | Smallest interval between values. |
| changeCount | Number of value changes. |

Statistic charts support these functions. Other charts and transformations may support a
subset or use different identifiers; follow their references. For cumulative counters,
calculate increase or rate in the query instead of summing samples.
