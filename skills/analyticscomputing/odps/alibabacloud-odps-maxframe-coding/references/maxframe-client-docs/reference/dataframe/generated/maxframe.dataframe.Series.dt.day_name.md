# maxframe.dataframe.Series.dt.day_name

#### Series.dt.day_name(\*args, \*\*kwargs)

Return the day names with specified locale.

* **Parameters:**
  **locale** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Locale determining the language in which to return the day name.
  Default is English locale (`'en_US.utf8'`). Use the command
  `locale -a` on your terminal on Unix systems to find your locale
  language code.
* **Returns:**
  Series or Index of day names.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(md.date_range(start='2018-01-01', freq='D', periods=3))
>>> s.execute()
0   2018-01-01
1   2018-01-02
2   2018-01-03
dtype: datetime64[ns]
>>> s.dt.day_name().execute()
0       Monday
1      Tuesday
2    Wednesday
dtype: object
```

```pycon
>>> idx = md.date_range(start='2018-01-01', freq='D', periods=3)
>>> idx.execute()
DatetimeIndex(['2018-01-01', '2018-01-02', '2018-01-03'],
              dtype='datetime64[ns]', freq='D')
>>> idx.day_name().execute()
Index(['Monday', 'Tuesday', 'Wednesday'], dtype='object')
```

Using the `locale` parameter you can set a different locale language,
for example: `idx.day_name(locale='pt_BR.utf8')` will return day
names in Brazilian Portuguese language.

```pycon
>>> idx = md.date_range(start='2018-01-01', freq='D', periods=3)
>>> idx.execute()
DatetimeIndex(['2018-01-01', '2018-01-02', '2018-01-03'],
              dtype='datetime64[ns]', freq='D')
>>> idx.day_name(locale='pt_BR.utf8')
Index(['Segunda', 'Terça', 'Quarta'], dtype='object')
```
