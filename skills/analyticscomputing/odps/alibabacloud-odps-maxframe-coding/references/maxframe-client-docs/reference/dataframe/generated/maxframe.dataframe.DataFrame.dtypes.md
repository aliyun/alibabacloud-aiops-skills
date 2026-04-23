# maxframe.dataframe.DataFrame.dtypes

#### *property* DataFrame.dtypes

Return the dtypes in the DataFrame.

This returns a Series with the data type of each column.
The result’s index is the original DataFrame’s columns. Columns
with mixed types are stored with the `object` dtype. See
[the User Guide](https://pandas.pydata.org/docs/user_guide/basics.html#basics-dtypes) for more.

* **Returns:**
  The data type of each column.
* **Return type:**
  [pandas.Series](https://pandas.pydata.org/docs/reference/api/pandas.Series.html#pandas.Series)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'float': [1.0],
...                    'int': [1],
...                    'datetime': [md.Timestamp('20180310')],
...                    'string': ['foo']})
>>> df.dtypes
float              float64
int                  int64
datetime    datetime64[ns]
string              object
dtype: object
```
