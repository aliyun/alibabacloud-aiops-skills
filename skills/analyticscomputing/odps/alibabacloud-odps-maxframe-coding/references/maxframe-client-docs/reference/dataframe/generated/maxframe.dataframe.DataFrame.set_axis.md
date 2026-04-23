# maxframe.dataframe.DataFrame.set_axis

#### DataFrame.set_axis(labels, axis=0, inplace=False)

Assign desired index to given axis.

Indexes for column or row labels can be changed by assigning
a list-like or Index.

* **Parameters:**
  * **labels** (*list-like* *,* [*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index)) – The values for the new index.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to update. The value 0 identifies the rows, and 1 identifies the columns.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to return a new DataFrame instance.
* **Returns:**
  **renamed** – An object of type DataFrame or None if `inplace=True`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None

#### SEE ALSO
[`DataFrame.rename_axis`](maxframe.dataframe.DataFrame.rename_axis.md#maxframe.dataframe.DataFrame.rename_axis)
: Alter the name of the index or columns.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
```

Change the row labels.

```pycon
>>> df.set_axis(['a', 'b', 'c'], axis='index').execute()
   A  B
a  1  4
b  2  5
c  3  6
```

Change the column labels.

```pycon
>>> df.set_axis(['I', 'II'], axis='columns').execute()
   I  II
0  1   4
1  2   5
2  3   6
```

Now, update the labels inplace.

```pycon
>>> df.set_axis(['i', 'ii'], axis='columns', inplace=True)
>>> df.execute()
   i  ii
0  1   4
1  2   5
2  3   6
```
