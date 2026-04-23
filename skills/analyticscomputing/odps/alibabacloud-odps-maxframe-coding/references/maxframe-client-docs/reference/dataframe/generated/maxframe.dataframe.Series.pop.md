# maxframe.dataframe.Series.pop

#### Series.pop(item)

Return item and drops from series. Raise KeyError if not found.

* **Parameters:**
  **item** (*label*) – Index of the element that needs to be removed.
* **Return type:**
  Value that is popped from series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> ser = md.Series([1,2,3])
```

```pycon
>>> ser.pop(0).execute()
1
```

```pycon
>>> ser.execute()
1    2
2    3
dtype: int64
```
