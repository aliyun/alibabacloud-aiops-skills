# maxframe.dataframe.Series.xs

#### Series.xs(key, axis=0, level=None, drop_level=True)

Return cross-section from the Series/DataFrame.

This method takes a key argument to select data at a particular
level of a MultiIndex.

* **Parameters:**
  * **key** (*label* *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *label*) – Label contained in the index, or partially in a MultiIndex.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Axis to retrieve cross-section on.
  * **level** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *defaults to first n levels* *(**n=1* *or* *len* *(**key* *)* *)*) – In case of a key partially contained in a MultiIndex, indicate
    which levels are used. Levels can be referred by label or position.
  * **drop_level** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If False, returns object with same levels as self.
* **Returns:**
  Cross-section from the original Series or DataFrame
  corresponding to the selected index levels.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Access a group of rows and columns by label(s) or a boolean array.

[`DataFrame.iloc`](maxframe.dataframe.DataFrame.iloc.md#maxframe.dataframe.DataFrame.iloc)
: Purely integer-location based indexing for selection by position.

### Notes

xs can not be used to set values.

MultiIndex Slicers is a generic way to get/set values on
any level or levels.
It is a superset of xs functionality, see
[MultiIndex Slicers](https://pandas.pydata.org/docs/user_guide/advanced.html#advanced-mi-slicers).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> d = {'num_legs': [4, 4, 2, 2],
...      'num_wings': [0, 0, 2, 2],
...      'class': ['mammal', 'mammal', 'mammal', 'bird'],
...      'animal': ['cat', 'dog', 'bat', 'penguin'],
...      'locomotion': ['walks', 'walks', 'flies', 'walks']}
>>> df = md.DataFrame(data=d)
>>> df = df.set_index(['class', 'animal', 'locomotion'])
>>> df.execute()
                            num_legs  num_wings
class  animal  locomotion
mammal cat     walks              4          0
        dog     walks              4          0
        bat     flies              2          2
bird   penguin walks              2          2
```

Get values at specified index

```pycon
>>> df.xs('mammal').execute()
                    num_legs  num_wings
animal locomotion
cat    walks              4          0
dog    walks              4          0
bat    flies              2          2
```

Get values at several indexes

```pycon
>>> df.xs(('mammal', 'dog')).execute()
            num_legs  num_wings
locomotion
walks              4          0
```

Get values at specified index and level

```pycon
>>> df.xs('cat', level=1).execute()
                    num_legs  num_wings
class  locomotion
mammal walks              4          0
```

Get values at several indexes and levels

```pycon
>>> df.xs(('bird', 'walks'),
...       level=[0, 'locomotion']).execute()
            num_legs  num_wings
animal
penguin         2          2
```

Get values at specified column and axis

```pycon
>>> df.xs('num_wings', axis=1).execute()
class   animal   locomotion
mammal  cat      walks         0
        dog      walks         0
        bat      flies         2
bird    penguin  walks         2
Name: num_wings, dtype: int64
```
