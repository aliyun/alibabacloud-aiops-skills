# maxframe.dataframe.DataFrame.swaplevel

#### DataFrame.swaplevel(i=-2, j=-1, axis=0)

Swap levels i and j in a `MultiIndex`.

Default is to swap the two innermost levels of the index.

* **Parameters:**
  * **i** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Levels of the indices to be swapped. Can pass level name as string.
  * **j** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Levels of the indices to be swapped. Can pass level name as string.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to swap levels on. 0 or ‘index’ for row-wise, 1 or
    ‘columns’ for column-wise.
* **Returns:**
  DataFrame with levels swapped in MultiIndex.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {"Grade": ["A", "B", "A", "C"]},
...     index=[
...         ["Final exam", "Final exam", "Coursework", "Coursework"],
...         ["History", "Geography", "History", "Geography"],
...         ["January", "February", "March", "April"],
...     ],
... )
>>> df.execute()
                                    Grade
Final exam  History     January      A
            Geography   February     B
Coursework  History     March        A
            Geography   April        C
```

In the following example, we will swap the levels of the indices.
Here, we will swap the levels column-wise, but levels can be swapped row-wise
in a similar manner. Note that column-wise is the default behaviour.
By not supplying any arguments for i and j, we swap the last and second to
last indices.

```pycon
>>> df.swaplevel().execute()
                                    Grade
Final exam  January     History         A
            February    Geography       B
Coursework  March       History         A
            April       Geography       C
```

By supplying one argument, we can choose which index to swap the last
index with. We can for example swap the first index with the last one as
follows.

```pycon
>>> df.swaplevel(0).execute()
                                    Grade
January     History     Final exam      A
February    Geography   Final exam      B
March       History     Coursework      A
April       Geography   Coursework      C
```

We can also define explicitly which indices we want to swap by supplying values
for both i and j. Here, we for example swap the first and second indices.

```pycon
>>> df.swaplevel(0, 1).execute()
                                    Grade
History     Final exam  January         A
Geography   Final exam  February        B
History     Coursework  March           A
Geography   Coursework  April           C
```
