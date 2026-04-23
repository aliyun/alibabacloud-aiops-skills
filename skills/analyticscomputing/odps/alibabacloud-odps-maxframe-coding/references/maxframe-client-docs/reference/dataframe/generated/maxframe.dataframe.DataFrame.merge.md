# maxframe.dataframe.DataFrame.merge

#### DataFrame.merge(right: DataFrame | Series, how: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'inner', on: [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, left_on: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, right_on: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, left_index: [bool](https://docs.python.org/3/library/functions.html#bool) = False, right_index: [bool](https://docs.python.org/3/library/functions.html#bool) = False, sort: [bool](https://docs.python.org/3/library/functions.html#bool) = False, suffixes: [Tuple](https://docs.python.org/3/library/typing.html#typing.Tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] = ('_x', '_y'), copy: [bool](https://docs.python.org/3/library/functions.html#bool) = True, indicator: [bool](https://docs.python.org/3/library/functions.html#bool) = False, validate: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, method: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'auto', auto_merge: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'both', auto_merge_threshold: [int](https://docs.python.org/3/library/functions.html#int) = 8, bloom_filter: [bool](https://docs.python.org/3/library/functions.html#bool) | [str](https://docs.python.org/3/library/stdtypes.html#str) = 'auto', bloom_filter_options: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] = None, left_hint: JoinHint = None, right_hint: JoinHint = None) → DataFrame

Merge DataFrame or named Series objects with a database-style join.

A named Series object is treated as a DataFrame with a single named column.

The join is done on columns or indexes. If joining columns on
columns, the DataFrame indexes *will be ignored*. Otherwise if joining indexes
on indexes or indexes on a column or columns, the index will be passed on.
When performing a cross merge, no column specifications to merge on are
allowed.

* **Parameters:**
  * **right** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *or* *named Series*) – Object to merge with.
  * **how** ( *{'left'* *,*  *'right'* *,*  *'outer'* *,*  *'inner'}* *,* *default 'inner'*) – 

    Type of merge to be performed.
    * left: use only keys from left frame, similar to a SQL left outer join;
      preserve key order.
    * right: use only keys from right frame, similar to a SQL right outer join;
      preserve key order.
    * outer: use union of keys from both frames, similar to a SQL full outer
      join; sort keys lexicographically.
    * inner: use intersection of keys from both frames, similar to a SQL inner
      join; preserve the order of the left keys.
  * **on** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list)) – Column or index level names to join on. These must be found in both
    DataFrames. If on is None and not merging on indexes then this defaults
    to the intersection of the columns in both DataFrames.
  * **left_on** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *, or* *array-like*) – Column or index level names to join on in the left DataFrame. Can also
    be an array or list of arrays of the length of the left DataFrame.
    These arrays are treated as if they are columns.
  * **right_on** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *, or* *array-like*) – Column or index level names to join on in the right DataFrame. Can also
    be an array or list of arrays of the length of the right DataFrame.
    These arrays are treated as if they are columns.
  * **left_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Use the index from the left DataFrame as the join key(s). If it is a
    MultiIndex, the number of keys in the other DataFrame (either the index
    or a number of columns) must match the number of levels.
  * **right_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Use the index from the right DataFrame as the join key. Same caveats as
    left_index.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Sort the join keys lexicographically in the result DataFrame. If False,
    the order of the join keys depends on the join type (how keyword).
  * **suffixes** (*list-like* *,* *default is* *(* *"_x"* *,*  *"_y"* *)*) – A length-2 sequence where each element is optionally a string
    indicating the suffix to add to overlapping column names in
    left and right respectively. Pass a value of None instead
    of a string to indicate that the column name from left or
    right should be left as-is, with no suffix. At least one of the
    values must not be None.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If False, avoid copy if possible.
  * **indicator** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default False*) – If True, adds a column to the output DataFrame called “_merge” with
    information on the source of each row. The column can be given a different
    name by providing a string argument. The column will have a Categorical
    type with the value of “left_only” for observations whose merge key only
    appears in the left DataFrame, “right_only” for observations
    whose merge key only appears in the right DataFrame, and “both”
    if the observation’s merge key is found in both DataFrames.
  * **validate** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – 

    If specified, checks if merge is of specified type.
    * ”one_to_one” or “1:1”: check if merge keys are unique in both
      left and right datasets.
    * ”one_to_many” or “1:m”: check if merge keys are unique in left
      dataset.
    * ”many_to_one” or “m:1”: check if merge keys are unique in right
      dataset.
    * ”many_to_many” or “m:m”: allowed, but does not result in checks.
  * **method** ( *{"auto"* *,*  *"shuffle"* *,*  *"broadcast"}* *,* *default auto*) – “broadcast” is recommended when one DataFrame is much smaller than the other,
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
  A DataFrame of the two merged objects.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df1 = md.DataFrame({'lkey': ['foo', 'bar', 'baz', 'foo'],
...                     'value': [1, 2, 3, 5]})
>>> df2 = md.DataFrame({'rkey': ['foo', 'bar', 'baz', 'foo'],
...                     'value': [5, 6, 7, 8]})
>>> df1.execute()
    lkey value
0   foo      1
1   bar      2
2   baz      3
3   foo      5
>>> df2.execute()
    rkey value
0   foo      5
1   bar      6
2   baz      7
3   foo      8
```

Merge df1 and df2 on the lkey and rkey columns. The value columns have
the default suffixes, \_x and \_y, appended.

```pycon
>>> df1.merge(df2, left_on='lkey', right_on='rkey').execute()
  lkey  value_x rkey  value_y
0  foo        1  foo        5
1  foo        1  foo        8
2  foo        5  foo        5
3  foo        5  foo        8
4  bar        2  bar        6
5  baz        3  baz        7
```

Merge DataFrames df1 and df2 with specified left and right suffixes
appended to any overlapping columns.

```pycon
>>> df1.merge(df2, left_on='lkey', right_on='rkey',
...           suffixes=('_left', '_right')).execute()
  lkey  value_left rkey  value_right
0  foo           1  foo            5
1  foo           1  foo            8
2  foo           5  foo            5
3  foo           5  foo            8
4  bar           2  bar            6
5  baz           3  baz            7
```

Merge DataFrames df1 and df2, but raise an exception if the DataFrames have
any overlapping columns.

```pycon
>>> df1.merge(df2, left_on='lkey', right_on='rkey', suffixes=(False, False)).execute()
Traceback (most recent call last):
...
ValueError: columns overlap but no suffix specified:
    Index(['value'], dtype='object')
```

```pycon
>>> df1 = md.DataFrame({'a': ['foo', 'bar'], 'b': [1, 2]})
>>> df2 = md.DataFrame({'a': ['foo', 'baz'], 'c': [3, 4]})
>>> df1.execute()
      a  b
0   foo  1
1   bar  2
>>> df2.execute()
      a  c
0   foo  3
1   baz  4
```

```pycon
>>> df1.merge(df2, how='inner', on='a').execute()
      a  b  c
0   foo  1  3
```

```pycon
>>> df1.merge(df2, how='left', on='a').execute()
      a  b  c
0   foo  1  3.0
1   bar  2  NaN
```
