# maxframe.dataframe.Series.unique

#### Series.unique(method='tree')

Uniques are returned in order of appearance. This does NOT sort.

* **Parameters:**
  * **values** (*1d array-like*)
  * **method** ( *'shuffle'* *or*  *'tree'* *,*  *'tree' method provide a better performance* *,*  *'shuffle'*)
  * **large.** (*is recommended if the number* *of* *unique values is very*)

#### SEE ALSO
`Index.unique`, [`Series.unique`](#maxframe.dataframe.Series.unique)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> import pandas as pd
>>> md.unique(md.Series([2, 1, 3, 3])).execute()
array([2, 1, 3])
```

```pycon
>>> md.unique(md.Series([2] + [1] * 5)).execute()
array([2, 1])
```

```pycon
>>> md.unique(md.Series([pd.Timestamp('20160101'),
...                     pd.Timestamp('20160101')])).execute()
array(['2016-01-01T00:00:00.000000000'], dtype='datetime64[ns]')
```

```pycon
>>> md.unique(md.Series([pd.Timestamp('20160101', tz='US/Eastern'),
...                      pd.Timestamp('20160101', tz='US/Eastern')])).execute()
array([Timestamp('2016-01-01 00:00:00-0500', tz='US/Eastern')],
      dtype=object)
```
