# maxframe.dataframe.Series.str.slice

#### Series.str.slice(start=None, stop=None, step=None)

Slice substrings from each element in the Series or Index.

* **Parameters:**
  * **start** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Start position for slice operation.
  * **stop** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Stop position for slice operation.
  * **step** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Step size for slice operation.
* **Returns:**
  Series or Index from sliced substring from original string object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [object](https://docs.python.org/3/library/functions.html#object)

#### SEE ALSO
`Series.str.slice_replace`
: Replace a slice with a string.

`Series.str.get`
: Return element at position. Equivalent to Series.str.slice(start=i, stop=i+1) with i being the position.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["koala", "dog", "chameleon"])
>>> s.execute()
0        koala
1          dog
2    chameleon
dtype: object
```

```pycon
>>> s.str.slice(start=1).execute()
0        oala
1          og
2    hameleon
dtype: object
```

```pycon
>>> s.str.slice(start=-1).execute()
0           a
1           g
2           n
dtype: object
```

```pycon
>>> s.str.slice(stop=2).execute()
0    ko
1    do
2    ch
dtype: object
```

```pycon
>>> s.str.slice(step=2).execute()
0      kaa
1       dg
2    caeen
dtype: object
```

```pycon
>>> s.str.slice(start=0, stop=5, step=3).execute()
0    kl
1     d
2    cm
dtype: object
```

Equivalent behaviour to:

```pycon
>>> s.str[0:5:3].execute()
0    kl
1     d
2    cm
dtype: object
```
