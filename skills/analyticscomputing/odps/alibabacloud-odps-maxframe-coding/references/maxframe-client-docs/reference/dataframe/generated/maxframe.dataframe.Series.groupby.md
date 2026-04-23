# maxframe.dataframe.Series.groupby

#### Series.groupby(by=None, level=None, as_index=True, sort=True, group_keys=True)

Group DataFrame using a mapper or by a Series of columns.

A groupby operation involves some combination of splitting the
object, applying a function, and combining the results. This can be
used to group large amounts of data and compute operations on these
groups.

* **Parameters:**
  * **by** (*mapping* *,* *function* *,* *label* *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *labels*) – Used to determine the groups for the groupby.
    If `by` is a function, it’s called on each value of the object’s
    index. If a dict or Series is passed, the Series or dict VALUES
    will be used to determine the groups (the Series’ values are first
    aligned; see `.align()` method). If an ndarray is passed, the
    values are used as-is to determine the groups. A label or list of
    labels may be passed to group by the columns in `self`. Notice
    that a tuple is interpreted as a (single) key.
  * **as_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – For aggregated output, return object with group labels as the
    index. Only relevant for DataFrame input. as_index=False is
    effectively “SQL-style” grouped output.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Sort group keys. Get better performance by turning this off.
    Note this does not influence the order of observations within each
    group. Groupby preserves the order of rows within each group.
  * **group_keys** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – When calling apply, add group keys to index to identify pieces.

### Notes

MaxFrame only supports groupby with axis=0.
Default value of group_keys will be decided given the version of local
pandas library, which is True since pandas 2.0.

* **Returns:**
  Returns a groupby object that contains information about the groups.
* **Return type:**
  DataFrameGroupBy

#### SEE ALSO
`resample`
: Convenience method for frequency conversion and resampling of time series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'Animal': ['Falcon', 'Falcon',
...                               'Parrot', 'Parrot'],
...                    'Max Speed': [380., 370., 24., 26.]})
>>> df.execute()
   Animal  Max Speed
0  Falcon      380.0
1  Falcon      370.0
2  Parrot       24.0
3  Parrot       26.0
>>> df.groupby(['Animal']).mean().execute()
        Max Speed
Animal
Falcon      375.0
Parrot       25.0
```
