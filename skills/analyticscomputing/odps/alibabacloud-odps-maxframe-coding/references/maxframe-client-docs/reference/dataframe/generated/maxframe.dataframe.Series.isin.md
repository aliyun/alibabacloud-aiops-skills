# maxframe.dataframe.Series.isin

#### Series.isin(values)

Whether elements in Series are contained in values.

Return a boolean Series showing whether each element in the Series
matches an element in the passed sequence of values exactly.

* **Parameters:**
  **values** ([*set*](https://docs.python.org/3/library/stdtypes.html#set) *or* *list-like*) – The sequence of values to test. Passing in a single string will
  raise a `TypeError`. Instead, turn a single string into a
  list of one element.
* **Returns:**
  Series of booleans indicating if each element is in values.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – 
  * If values is a string

#### SEE ALSO
`DataFrame.isin`
: Equivalent method on DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['lame', 'cow', 'lame', 'beetle', 'lame',
...                'hippo'], name='animal')
>>> s.isin(['cow', 'lame']).execute()
0     True
1     True
2     True
3    False
4     True
5    False
Name: animal, dtype: bool
```

Passing a single string as `s.isin('lame')` will raise an error. Use
a list of one element instead:

```pycon
>>> s.isin(['lame']).execute()
0     True
1    False
2     True
3    False
4     True
5    False
Name: animal, dtype: bool
```
