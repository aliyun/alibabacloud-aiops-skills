# maxframe.dataframe.DataFrame.between_time

#### DataFrame.between_time(start_time, end_time, inclusive='both', axis=0)

Select values between particular times of the day (e.g., 9:00-9:30 AM).

By setting `start_time` to be later than `end_time`,
you can get the times that are *not* between the two times.

* **Parameters:**
  * **start_time** ([*datetime.time*](https://docs.python.org/3/library/datetime.html#datetime.time) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Initial time as a time filter limit.
  * **end_time** ([*datetime.time*](https://docs.python.org/3/library/datetime.html#datetime.time) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – End time as a time filter limit.
  * **inclusive** ( *{"both"* *,*  *"neither"* *,*  *"left"* *,*  *"right"}* *,* *default "both"*) – Include boundaries; whether to set each bound as closed or open.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Determine range time on index or columns value.
    For Series this parameter is unused and defaults to 0.
* **Returns:**
  Data from the original object filtered to the specified dates range.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If the index is not  a `DatetimeIndex`

#### SEE ALSO
[`at_time`](maxframe.dataframe.DataFrame.at_time.md#maxframe.dataframe.DataFrame.at_time)
: Select values at a particular time of the day.

`first`
: Select initial periods of time series based on a date offset.

`last`
: Select final periods of time series based on a date offset.

`DatetimeIndex.indexer_between_time`
: Get just the index locations for values between particular times of the day.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> i = md.date_range('2018-04-09', periods=4, freq='1D20min')
>>> ts = md.DataFrame({'A': [1, 2, 3, 4]}, index=i)
>>> ts.execute()
                     A
2018-04-09 00:00:00  1
2018-04-10 00:20:00  2
2018-04-11 00:40:00  3
2018-04-12 01:00:00  4
```

```pycon
>>> ts.between_time('0:15', '0:45').execute()
                     A
2018-04-10 00:20:00  2
2018-04-11 00:40:00  3
```

You get the times that are *not* between two times by setting
`start_time` later than `end_time`:

```pycon
>>> ts.between_time('0:45', '0:15').execute()
                     A
2018-04-09 00:00:00  1
2018-04-12 01:00:00  4
```
