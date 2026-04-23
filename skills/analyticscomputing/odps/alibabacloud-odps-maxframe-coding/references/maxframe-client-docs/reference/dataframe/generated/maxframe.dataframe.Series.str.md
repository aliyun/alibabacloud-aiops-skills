# maxframe.dataframe.Series.str

#### Series.str()

Vectorized string functions for Series and Index.
NAs stay NA unless handled otherwise by a particular method.
Patterned after Python’s string methods, with some inspiration from
R’s stringr package.
.. rubric:: Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["A_Str_Series"])
>>> s.execute()
0    A_Str_Series
dtype: object
>>> s.str.split("_").execute()
0    [A, Str, Series]
dtype: object
>>> s.str.replace("_", "").execute()
0    AStrSeries
dtype: object
```
