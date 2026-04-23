# maxframe.dataframe.DataFrame.at_time

#### DataFrame.at_time(time, axis=0)

Select values at particular time of day (e.g., 9:30AM).

* **Parameters:**
  * **time** ([*datetime.time*](https://docs.python.org/3/library/datetime.html#datetime.time) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The values to select.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – For Series this parameter is unused and defaults to 0.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If the index is not  a `DatetimeIndex`

#### SEE ALSO
[`between_time`](maxframe.dataframe.DataFrame.between_time.md#maxframe.dataframe.DataFrame.between_time)
: Select values between particular times of the day.

`first`
: Select initial periods of time series based on a date offset.

`last`
: Select final periods of time series based on a date offset.

`DatetimeIndex.indexer_at_time`
: Get just the index locations for values at particular time of the day.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> i = md.date_range('2018-04-09', periods=4, freq='12h')
>>> ts = md.DataFrame({'A': [1, 2, 3, 4]}, index=i)
>>> ts.execute()
                     A
2018-04-09 00:00:00  1
2018-04-09 12:00:00  2
2018-04-10 00:00:00  3
2018-04-10 12:00:00  4
```

```pycon
>>> ts.at_time('12:00').execute()
                     A
2018-04-09 12:00:00  2
2018-04-10 12:00:00  4
```
