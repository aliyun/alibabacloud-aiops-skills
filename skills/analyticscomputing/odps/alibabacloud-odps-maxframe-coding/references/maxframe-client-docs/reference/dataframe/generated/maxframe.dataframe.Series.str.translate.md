# maxframe.dataframe.Series.str.translate

#### Series.str.translate(table)

Map all characters in the string through the given mapping table.

Equivalent to standard [`str.translate()`](https://docs.python.org/3/library/stdtypes.html#str.translate).

* **Parameters:**
  **table** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Table is a mapping of Unicode ordinals to Unicode ordinals, strings, or
  None. Unmapped characters are left untouched.
  Characters mapped to None are deleted. [`str.maketrans()`](https://docs.python.org/3/library/stdtypes.html#str.maketrans) is a
  helper function for making translation tables.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> ser = md.Series(["El niño", "Françoise"])
>>> mytable = str.maketrans({'ñ': 'n', 'ç': 'c'})
>>> ser.str.translate(mytable).execute()
0   El nino
1   Francoise
dtype: object
```
