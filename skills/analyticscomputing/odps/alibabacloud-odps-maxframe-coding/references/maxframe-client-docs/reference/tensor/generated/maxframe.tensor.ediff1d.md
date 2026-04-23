# maxframe.tensor.ediff1d

### maxframe.tensor.ediff1d(a, to_end=None, to_begin=None)

The differences between consecutive elements of a tensor.

* **Parameters:**
  * **a** (*array_like*) – If necessary, will be flattened before the differences are taken.
  * **to_end** (*array_like* *,* *optional*) – Number(s) to append at the end of the returned differences.
  * **to_begin** (*array_like* *,* *optional*) – Number(s) to prepend at the beginning of the returned differences.
* **Returns:**
  **ediff1d** – The differences. Loosely, this is `a.flat[1:] - a.flat[:-1]`.
* **Return type:**
  Tensor

#### SEE ALSO
[`diff`](maxframe.tensor.diff.md#maxframe.tensor.diff), `gradient`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([1, 2, 4, 7, 0])
>>> mt.ediff1d(x).execute()
array([ 1,  2,  3, -7])
```

```pycon
>>> mt.ediff1d(x, to_begin=-99, to_end=mt.array([88, 99])).execute()
array([-99,   1,   2,   3,  -7,  88,  99])
```

The returned tensor is always 1D.

```pycon
>>> y = [[1, 2, 4], [1, 6, 24]]
>>> mt.ediff1d(y).execute()
array([ 1,  2, -3,  5, 18])
```
