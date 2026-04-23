# maxframe.dataframe.DataFrame.join

#### DataFrame.join(other: DataFrame | Series, on: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, how: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'left', lsuffix: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', rsuffix: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', sort: [bool](https://docs.python.org/3/library/functions.html#bool) = False, method: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, auto_merge: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'both', auto_merge_threshold: [int](https://docs.python.org/3/library/functions.html#int) = 8, bloom_filter: [bool](https://docs.python.org/3/library/functions.html#bool) | [Dict](https://docs.python.org/3/library/typing.html#typing.Dict) = True, bloom_filter_options: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] = None, left_hint: JoinHint = None, right_hint: JoinHint = None) → DataFrame

Join columns of another DataFrame.

Join columns with other DataFrame either on index or on a key
column. Efficiently join multiple DataFrame objects by index at once by
passing a list.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Index should be similar to one of the columns in this one. If a
    Series is passed, its name attribute must be set, and that will be
    used as the column name in the resulting joined DataFrame.
  * **on** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *, or* *array-like* *,* *optional*) – Column or index level name(s) in the caller to join on the index
    in other, otherwise joins index-on-index. If multiple
    values given, the other DataFrame must have a MultiIndex. Can
    pass an array as the join key if it is not already contained in
    the calling DataFrame. Like an Excel VLOOKUP operation.
  * **how** ( *{'left'* *,*  *'right'* *,*  *'outer'* *,*  *'inner'}* *,* *default 'left'*) – 

    How to handle the operation of the two objects.
    * left: use calling frame’s index (or column if on is specified)
    * right: use other’s index.
    * outer: form union of calling frame’s index (or column if on is
      specified) with other’s index, and sort it.
      lexicographically.
    * inner: form intersection of calling frame’s index (or column if
      on is specified) with other’s index, preserving the order
      of the calling’s one.
  * **lsuffix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default ''*) – Suffix to use from left frame’s overlapping columns.
  * **rsuffix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default ''*) – Suffix to use from right frame’s overlapping columns.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Order result DataFrame lexicographically by the join key. If False,
    the order of the join key depends on the join type (how keyword).
  * **method** ( *{"shuffle"* *,*  *"broadcast"}* *,* *default None*) – “broadcast” is recommended when one DataFrame is much smaller than the other,
    otherwise, “shuffle” will be a better choice. By default, we choose method
    according to actual data size.
  * **auto_merge** ( *{"both"* *,*  *"none"* *,*  *"before"* *,*  *"after"}* *,* *default both*) – 

    Auto merge small chunks before or after merge
    * ”both”: auto merge small chunks before and after,
    * ”none”: do not merge small chunks
    * ”before”: only merge small chunks before merge
    * ”after”: only merge small chunks after merge
  * **auto_merge_threshold** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 8*) – When how is “inner”, merged result could be much smaller than original DataFrame,
    if the number of chunks is greater than the threshold,
    it will merge small chunks automatically.
  * **bloom_filter** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default "auto"*) – Use bloom filter to optimize merge
  * **bloom_filter_options** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – 
    * “max_elements”: max elements in bloom filter,
      default value is the max size of all input chunks
    * ”error_rate”: error raite, default 0.1.
    * ”apply_chunk_size_threshold”: min chunk size of input chunks to apply bloom filter, default 10
      when chunk size of left and right is greater than this threshold, apply bloom filter
    * ”filter”: “large”, “small”, “both”, default “large”
      decides to filter on large, small or both DataFrames.
  * **left_hint** (*JoinHint* *,* *default None*) – Join strategy to use for left frame. When data skew occurs, consider these strategies to avoid long-tail issues,
    but use them cautiously to prevent OOM and unnecessary overhead.
  * **right_hint** (*JoinHint* *,* *default None*) – Join strategy to use for right frame.
* **Returns:**
  A dataframe containing columns from both the caller and other.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.merge`](maxframe.dataframe.DataFrame.merge.md#maxframe.dataframe.DataFrame.merge)
: For column(s)-on-column(s) operations.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'key': ['K0', 'K1', 'K2', 'K3', 'K4', 'K5'],
...                    'A': ['A0', 'A1', 'A2', 'A3', 'A4', 'A5']})
```

```pycon
>>> df.execute()
  key   A
0  K0  A0
1  K1  A1
2  K2  A2
3  K3  A3
4  K4  A4
5  K5  A5
```

```pycon
>>> other = md.DataFrame({'key': ['K0', 'K1', 'K2'],
...                       'B': ['B0', 'B1', 'B2']})
```

```pycon
>>> other.execute()
  key   B
0  K0  B0
1  K1  B1
2  K2  B2
```

Join DataFrames using their indexes.

```pycon
>>> df.join(other, lsuffix='_caller', rsuffix='_other').execute()
  key_caller   A key_other    B
0         K0  A0        K0   B0
1         K1  A1        K1   B1
2         K2  A2        K2   B2
3         K3  A3       NaN  NaN
4         K4  A4       NaN  NaN
5         K5  A5       NaN  NaN
```

If we want to join using the key columns, we need to set key to be
the index in both df and other. The joined DataFrame will have
key as its index.

```pycon
>>> df.set_index('key').join(other.set_index('key')).execute()
      A    B
key
K0   A0   B0
K1   A1   B1
K2   A2   B2
K3   A3  NaN
K4   A4  NaN
K5   A5  NaN
```

Another option to join using the key columns is to use the on
parameter. DataFrame.join always uses other’s index but we can use
any column in df. This method preserves the original DataFrame’s
index in the result.

```pycon
>>> df.join(other.set_index('key'), on='key').execute()
  key   A    B
0  K0  A0   B0
1  K1  A1   B1
2  K2  A2   B2
3  K3  A3  NaN
4  K4  A4  NaN
5  K5  A5  NaN
```

Using non-unique key values shows how they are matched.

```pycon
>>> df = md.DataFrame({'key': ['K0', 'K1', 'K1', 'K3', 'K0', 'K1'],
...                    'A': ['A0', 'A1', 'A2', 'A3', 'A4', 'A5']})
```

```pycon
>>> df.execute()
  key   A
0  K0  A0
1  K1  A1
2  K1  A2
3  K3  A3
4  K0  A4
5  K1  A5
```

```pycon
>>> df.join(other.set_index('key'), on='key').execute()
  key   A    B
0  K0  A0   B0
1  K1  A1   B1
2  K1  A2   B1
3  K3  A3  NaN
4  K0  A4   B0
5  K1  A5   B1
```
