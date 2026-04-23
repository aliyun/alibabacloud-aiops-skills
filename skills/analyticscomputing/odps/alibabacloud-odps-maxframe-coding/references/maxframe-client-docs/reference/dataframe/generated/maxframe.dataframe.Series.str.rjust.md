# maxframe.dataframe.Series.str.rjust

#### Series.str.rjust(width: [int](https://docs.python.org/3/library/functions.html#int), fillchar: [str](https://docs.python.org/3/library/stdtypes.html#str) = ' ')

Pad left side of strings in the Series/Index.

Equivalent to [`str.rjust()`](https://docs.python.org/3/library/stdtypes.html#str.rjust).

* **Parameters:**
  * **width** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Minimum width of resulting string; additional characters will be filled
    with `fillchar`.
  * **fillchar** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Additional character for filling, default is whitespace.
* **Return type:**
  Series/Index of objects.

### Examples

For Series.str.center:

```pycon
>>> import maxframe.dataframe as md
>>> ser = md.Series(['dog', 'bird', 'mouse'])
>>> ser.str.center(8, fillchar='.').execute()
0   ..dog...
1   ..bird..
2   .mouse..
dtype: object
```

For Series.str.ljust:

```pycon
>>> ser = md.Series(['dog', 'bird', 'mouse'])
>>> ser.str.ljust(8, fillchar='.').execute()
0   dog.....
1   bird....
2   mouse...
dtype: object
```

For Series.str.rjust:

```pycon
>>> ser = md.Series(['dog', 'bird', 'mouse'])
>>> ser.str.rjust(8, fillchar='.').execute()
0   .....dog
1   ....bird
2   ...mouse
dtype: object
```
