# maxframe.dataframe.Series.dt.weekofyear

#### Series.dt.weekofyear

The week ordinal of the year.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.PeriodIndex(["2023-01", "2023-02", "2023-03"], freq="M")
>>> idx.week  # It can be written `weekofyear`.execute()
Index([5, 9, 13], dtype='int64')
```
