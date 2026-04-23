# maxframe.dataframe.DataFrame.pop

#### DataFrame.pop(item)

Return item and drop from frame. Raise KeyError if not found.

* **Parameters:**
  **item** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Label of column to be popped.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([('falcon', 'bird', 389.0),
...                    ('parrot', 'bird', 24.0),
...                    ('lion', 'mammal', 80.5),
...                    ('monkey', 'mammal', np.nan)],
...                   columns=('name', 'class', 'max_speed'))
>>> df.execute()
     name   class  max_speed
0  falcon    bird      389.0
1  parrot    bird       24.0
2    lion  mammal       80.5
3  monkey  mammal        NaN
```

```pycon
>>> df.pop('class').execute()
0      bird
1      bird
2    mammal
3    mammal
Name: class, dtype: object
```

```pycon
>>> df.execute()
     name  max_speed
0  falcon      389.0
1  parrot       24.0
2    lion       80.5
3  monkey        NaN
```
