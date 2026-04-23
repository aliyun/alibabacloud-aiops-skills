# maxframe.dataframe.Series.swaplevel

#### Series.swaplevel(i=-2, j=-1)

Swap levels i and j in a `MultiIndex`.

Default is to swap the two innermost levels of the index.

* **Parameters:**
  * **i** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Levels of the indices to be swapped. Can pass level name as string.
  * **j** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Levels of the indices to be swapped. Can pass level name as string.
* **Returns:**
  Series with levels swapped in MultiIndex.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(
...     ["A", "B", "A", "C"],
...     index=[
...         ["Final exam", "Final exam", "Coursework", "Coursework"],
...         ["History", "Geography", "History", "Geography"],
...         ["January", "February", "March", "April"],
...     ],
... )
>>> s.execute()
Final exam  History     January      A
            Geography   February     B
Coursework  History     March        A
            Geography   April        C
dtype: object
```

In the following example, we will swap the levels of the indices.
Here, we will swap the levels column-wise, but levels can be swapped row-wise
in a similar manner. Note that column-wise is the default behaviour.
By not supplying any arguments for i and j, we swap the last and second to
last indices.

```pycon
>>> s.swaplevel().execute()
Final exam  January     History         A
            February    Geography       B
Coursework  March       History         A
            April       Geography       C
dtype: object
```

By supplying one argument, we can choose which index to swap the last
index with. We can for example swap the first index with the last one as
follows.

```pycon
>>> s.swaplevel(0).execute()
January     History     Final exam      A
February    Geography   Final exam      B
March       History     Coursework      A
April       Geography   Coursework      C
dtype: object
```

We can also define explicitly which indices we want to swap by supplying values
for both i and j. Here, we for example swap the first and second indices.

```pycon
>>> s.swaplevel(0, 1).execute()
History     Final exam  January         A
Geography   Final exam  February        B
History     Coursework  March           A
Geography   Coursework  April           C
dtype: object
```
