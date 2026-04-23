# maxframe.dataframe.Index.to_frame

#### Index.to_frame(index: [bool](https://docs.python.org/3/library/functions.html#bool) = True, name=None)

Create a DataFrame with a column containing the Index.

* **Parameters:**
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Set the index of the returned DataFrame as the original Index.
  * **name** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default None*) – The passed name should substitute for the index name (if it has
    one).
* **Returns:**
  DataFrame containing the original Index data.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Index.to_series`](maxframe.dataframe.Index.to_series.md#maxframe.dataframe.Index.to_series)
: Convert an Index to a Series.

[`Series.to_frame`](maxframe.dataframe.Series.to_frame.md#maxframe.dataframe.Series.to_frame)
: Convert Series to DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.Index(['Ant', 'Bear', 'Cow'], name='animal')
>>> idx.to_frame().execute()
       animal
animal
Ant       Ant
Bear     Bear
Cow       Cow
```

By default, the original Index is reused. To enforce a new Index:

```pycon
>>> idx.to_frame(index=False).execute()
  animal
0    Ant
1   Bear
2    Cow
```

To override the name of the resulting column, specify name:

```pycon
>>> idx.to_frame(index=False, name='zoo').execute()
    zoo
0   Ant
1  Bear
2   Cow
```
