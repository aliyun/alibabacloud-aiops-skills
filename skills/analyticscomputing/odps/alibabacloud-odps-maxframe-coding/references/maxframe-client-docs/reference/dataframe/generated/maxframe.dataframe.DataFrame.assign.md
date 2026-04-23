# maxframe.dataframe.DataFrame.assign

#### DataFrame.assign(\*\*kwargs)

Assign new columns to a DataFrame.
Returns a new object with all original columns in addition to new ones.
Existing columns that are re-assigned will be overwritten.

* **Parameters:**
  **\*\*kwargs** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *of*  *{str: callable* *or* *Series}*) – The column names are keywords. If the values are
  callable, they are computed on the DataFrame and
  assigned to the new columns. The callable must not
  change input DataFrame (though pandas doesn’t check it).
  If the values are not callable, (e.g. a Series, scalar, or array),
  they are simply assigned.
* **Returns:**
  A new DataFrame with the new columns in addition to
  all the existing columns.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Notes

Assigning multiple columns within the same `assign` is possible.
Later items in ‘kwargs’ may refer to newly created or modified
columns in ‘df’; items are computed and assigned into ‘df’ in order.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'temp_c': [17.0, 25.0]},
...                   index=['Portland', 'Berkeley'])
>>> df.execute()
          temp_c
Portland    17.0
Berkeley    25.0
```

Where the value is a callable, evaluated on df:

```pycon
>>> df.assign(temp_f=lambda x: x.temp_c * 9 / 5 + 32).execute()
          temp_c  temp_f
Portland    17.0    62.6
Berkeley    25.0    77.0
```

Alternatively, the same behavior can be achieved by directly
referencing an existing Series or sequence:

```pycon
>>> df.assign(temp_f=df['temp_c'] * 9 / 5 + 32).execute()
          temp_c  temp_f
Portland    17.0    62.6
Berkeley    25.0    77.0
```

You can create multiple columns within the same assign where one
of the columns depends on another one defined within the same assign:

```pycon
>>> df.assign(temp_f=lambda x: x['temp_c'] * 9 / 5 + 32,
...           temp_k=lambda x: (x['temp_f'] +  459.67) * 5 / 9).execute()
          temp_c  temp_f  temp_k
Portland    17.0    62.6  290.15
Berkeley    25.0    77.0  298.15
```
