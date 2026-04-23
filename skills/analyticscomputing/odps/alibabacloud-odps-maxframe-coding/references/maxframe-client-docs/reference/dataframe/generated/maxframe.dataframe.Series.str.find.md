# maxframe.dataframe.Series.str.find

#### Series.str.find(sub, start: [int](https://docs.python.org/3/library/functions.html#int) = 0, end=None)

Return lowest indexes in each strings in the Series/Index.

Each of returned indexes corresponds to the position where the
substring is fully contained between [start:end]. Return -1 on
failure. Equivalent to standard [`str.find()`](https://docs.python.org/3/library/stdtypes.html#str.find).

* **Parameters:**
  * **sub** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Substring being searched.
  * **start** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Left edge index.
  * **end** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Right edge index.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of int.

#### SEE ALSO
[`rfind`](maxframe.dataframe.Series.str.rfind.md#maxframe.dataframe.Series.str.rfind)
: Return highest indexes in each strings.

### Examples

For Series.str.find:

```pycon
>>> import maxframe.dataframe as md
>>> ser = md.Series(["cow_", "duck_", "do_ve"])
>>> ser.str.find("_").execute()
0   3
1   4
2   2
dtype: int64
```

For Series.str.rfind:

```pycon
>>> ser = md.Series(["_cow_", "duck_", "do_v_e"])
>>> ser.str.rfind("_").execute()
0   4
1   4
2   4
dtype: int64
```
