# maxframe.dataframe.DataFrame.mf.extract_kv

#### DataFrame.mf.extract_kv(columns=None, kv_delim='=', item_delim=',', dtype='float', fill_value=None, errors='raise')

Extract values in key-value represented columns into standalone columns.
New column names will be the name of the key-value column followed by
an underscore and the key.

* **Parameters:**
  * **columns** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default None*) – The key-value columns to be extracted.
  * **kv_delim** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '='*) – Delimiter between key and value.
  * **item_delim** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '* *,* *'*) – Delimiter between key-value pairs.
  * **dtype** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Type of value columns to generate.
  * **fill_value** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default None*) – Default value for missing key-value pairs.
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'raise'*) – 
    * If ‘raise’, then invalid parsing will raise an exception.
    * If ‘ignore’, then invalid parsing will return the input.
* **Returns:**
  extracted data frame
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.mf.collect_kv`](maxframe.dataframe.DataFrame.mf.collect_kv.md#maxframe.dataframe.DataFrame.mf.collect_kv)

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({"name": ["name1", "name2", "name3", "name4", "name5"],
...                    "kv": ["k1=1.0,k2=3.0,k5=10.0",
...                           "k2=3.0,k3=5.1",
...                           "k1=7.1,k7=8.2",
...                           "k2=1.2,k3=1.5",
...                           "k2=1.0,k9=1.1"]})
>>> df.execute()
   name   kv
0  name1  k1=1.0,k2=3.0,k5=10.0
1  name2  k2=3.0,k3=5.1
2  name3  k1=7.1,k7=8.2
3  name4  k2=1.2,k3=1.5
4  name5  k2=1.0,k9=1.1
```

The field names to be expanded are specified by columns
kv_delim is to delimit the key and value and ‘=’ is default
item_delim is to delimit the Key-Value pairs, ‘,’ is default
The output field name is the original field name connect with the key by “_”
fill_value is used to fill missing values, None is default

```pycon
>>> df.mf.extract_kv(columns=['kv'], kv_delim='=', item_delim=',').execute()
   name   kv_k1   kv_k2   kv_k3   kv_k5   kv_k7   kv_k9
0  name1  1.0     3.0     NaN     10.0    NaN     NaN
1  name2  NaN     3.0     5.1     NaN     NaN     NaN
2  name3  7.1     NaN     NaN     NaN     8.2     NaN
3  name4  NaN     1.2     1.5     NaN     NaN     NaN
4  name5  NaN     1.0     NaN     NaN     NaN     1.1
```
