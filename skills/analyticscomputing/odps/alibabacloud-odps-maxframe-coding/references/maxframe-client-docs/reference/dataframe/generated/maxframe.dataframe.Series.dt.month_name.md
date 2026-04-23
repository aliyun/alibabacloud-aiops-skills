# maxframe.dataframe.Series.dt.month_name

#### Series.dt.month_name(\*args, \*\*kwargs)

Return the month names with specified locale.

* **Parameters:**
  **locale** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Locale determining the language in which to return the month name.
  Default is English locale (`'en_US.utf8'`). Use the command
  `locale -a` on your terminal on Unix systems to find your locale
  language code.
* **Returns:**
  Series or Index of month names.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(md.date_range(start='2018-01', freq='ME', periods=3))
>>> s.execute()
0   2018-01-31
1   2018-02-28
2   2018-03-31
dtype: datetime64[ns]
>>> s.dt.month_name().execute()
0     January
1    February
2       March
dtype: object
```

```pycon
>>> idx = md.date_range(start='2018-01', freq='ME', periods=3)
>>> idx.execute()
DatetimeIndex(['2018-01-31', '2018-02-28', '2018-03-31'],
              dtype='datetime64[ns]', freq='ME')
>>> idx.month_name().execute()
Index(['January', 'February', 'March'], dtype='object')
```

Using the `locale` parameter you can set a different locale language,
for example: `idx.month_name(locale='pt_BR.utf8')` will return month
names in Brazilian Portuguese language.

```pycon
>>> idx = md.date_range(start='2018-01', freq='ME', periods=3)
>>> idx.execute()
DatetimeIndex(['2018-01-31', '2018-02-28', '2018-03-31'],
              dtype='datetime64[ns]', freq='ME')
>>> idx.month_name(locale='pt_BR.utf8')
Index(['Janeiro', 'Fevereiro', 'Março'], dtype='object')
```
