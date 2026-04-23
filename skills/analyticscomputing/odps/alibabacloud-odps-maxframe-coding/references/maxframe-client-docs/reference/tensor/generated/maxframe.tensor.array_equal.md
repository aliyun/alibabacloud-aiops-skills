# maxframe.tensor.array_equal

### maxframe.tensor.array_equal(a1, a2)

True if two tensors have the same shape and elements, False otherwise.

* **Parameters:**
  * **a1** (*array_like*) – Input arrays.
  * **a2** (*array_like*) – Input arrays.
* **Returns:**
  **b** – Returns True if the tensors are equal.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`allclose`](maxframe.tensor.allclose.md#maxframe.tensor.allclose)
: Returns True if two tensors are element-wise equal within a tolerance.

`array_equiv`
: Returns True if input tensors are shape consistent and all elements equal.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.array_equal([1, 2], [1, 2]).execute()
True
>>> mt.array_equal(mt.array([1, 2]), mt.array([1, 2])).execute()
True
>>> mt.array_equal([1, 2], [1, 2, 3]).execute()
False
>>> mt.array_equal([1, 2], [1, 4]).execute()
False
```
