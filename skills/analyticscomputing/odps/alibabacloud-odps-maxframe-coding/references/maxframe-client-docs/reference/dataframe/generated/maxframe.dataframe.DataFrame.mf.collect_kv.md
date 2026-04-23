# maxframe.dataframe.DataFrame.mf.collect_kv

#### DataFrame.mf.collect_kv(columns=None, kv_delim='=', item_delim=',', kv_col='kv_col')

Merge values in specified columns into a key-value represented column.

* **Parameters:**
  * **columns** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default None*) – The columns to be merged.
  * **kv_delim** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '='*) – Delimiter between key and value.
  * **item_delim** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '* *,* *'*) – Delimiter between key-value pairs.
  * **kv_col** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'kv_col'*) – Name of the new key-value column
* **Returns:**
  converted data frame
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.mf.extract_kv`](maxframe.dataframe.DataFrame.mf.extract_kv.md#maxframe.dataframe.DataFrame.mf.extract_kv)

### Examples

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({"name": ["name1", "name2", "name3", "name4", "name5"],
...                    "k1": [1.0, NaN, 7.1, NaN, NaN],
...                    "k2": [3.0, 3.0, NaN, 1.2, 1.0],
...                    "k3": [NaN, 5.1, NaN, 1.5, NaN],
...                    "k5": [10.0, NaN, NaN, NaN, NaN,],
...                    "k7": [NaN, NaN, 8.2, NaN, NaN, ],
...                    "k9": [NaN, NaN, NaN, NaN, 1.1]})
>>> df.execute()
   name   k1   k2   k3   k5    k7   k9
0  name1  1.0  3.0  NaN  10.0  NaN  NaN
1  name2  NaN  3.0  5.1  NaN   NaN  NaN
2  name3  7.1  NaN  NaN  NaN   8.2  NaN
3  name4  NaN  1.2  1.5  NaN   NaN  NaN
4  name5  NaN  1.0  NaN  NaN   NaN  1.1
```

The field names to be merged are specified by columns
kv_delim is to delimit the key and value and ‘=’ is default
item_delim is to delimit the Key-Value pairs, ‘,’ is default
The new column name is specified by kv_col, ‘kv_col’ is default

```pycon
>>> df.mf.collect_kv(columns=['k1', 'k2', 'k3', 'k5', 'k7', 'k9']).execute()
   name   kv_col
0  name1  k1=1.0,k2=3.0,k5=10.0
1  name2  k2=3.0,k3=5.1
2  name3  k1=7.1,k7=8.2
3  name4  k2=1.2,k3=1.5
4  name5  k2=1.0,k9=1.1
```
