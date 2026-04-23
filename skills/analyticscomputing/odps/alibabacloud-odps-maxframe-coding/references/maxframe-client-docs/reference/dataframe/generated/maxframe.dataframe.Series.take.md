# maxframe.dataframe.Series.take

#### Series.take(indices, axis=0, \*\*kwargs)

Return the elements in the given *positional* indices along an axis.

This means that we are not indexing according to actual values in
the index attribute of the object. We are indexing according to the
actual position of the element in the object.

* **Parameters:**
  * **indices** (*array-like*) – An array of ints indicating which positions to take.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'* *,* *None}* *,* *default 0*) – The axis on which to select elements. `0` means that we are
    selecting rows, `1` means that we are selecting columns.
    For Series this parameter is unused and defaults to 0.
  * **\*\*kwargs** – For compatibility with `numpy.take()`. Has no effect on the
    output.
* **Returns:**
  An array-like containing the elements taken from the object.
* **Return type:**
  same type as caller

#### SEE ALSO
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Select a subset of a DataFrame by labels.

[`DataFrame.iloc`](maxframe.dataframe.DataFrame.iloc.md#maxframe.dataframe.DataFrame.iloc)
: Select a subset of a DataFrame by positions.

[`numpy.take`](https://numpy.org/doc/stable/reference/generated/numpy.take.html#numpy.take)
: Take elements from an array along an axis.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([('falcon', 'bird', 389.0),
...                    ('parrot', 'bird', 24.0),
...                    ('lion', 'mammal', 80.5),
...                    ('monkey', 'mammal', mt.nan)],
...                   columns=['name', 'class', 'max_speed'],
...                   index=[0, 2, 3, 1])
>>> df.execute()
     name   class  max_speed
0  falcon    bird      389.0
2  parrot    bird       24.0
3    lion  mammal       80.5
1  monkey  mammal        NaN
```

Take elements at positions 0 and 3 along the axis 0 (default).

Note how the actual indices selected (0 and 1) do not correspond to
our selected indices 0 and 3. That’s because we are selecting the 0th
and 3rd rows, not rows whose indices equal 0 and 3.

```pycon
>>> df.take([0, 3]).execute()
     name   class  max_speed
0  falcon    bird      389.0
1  monkey  mammal        NaN
```

Take elements at indices 1 and 2 along the axis 1 (column selection).

```pycon
>>> df.take([1, 2], axis=1).execute()
    class  max_speed
0    bird      389.0
2    bird       24.0
3  mammal       80.5
1  mammal        NaN
```

We may take elements using negative integers for positive indices,
starting from the end of the object, just like with Python lists.

```pycon
>>> df.take([-1, -2]).execute()
     name   class  max_speed
1  monkey  mammal        NaN
3    lion  mammal       80.5
```
