# maxframe.tensor.full_like

### maxframe.tensor.full_like(a, fill_value, dtype=None, gpu=None, order='K')

Return a full tensor with the same shape and type as a given tensor.

* **Parameters:**
  * **a** (*array_like*) – The shape and data-type of a define these same attributes of
    the returned tensor.
  * **fill_value** (*scalar*) – Fill value.
  * **dtype** (*data-type* *,* *optional*) – Overrides the data type of the result.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, None as default
  * **order** ( *{'C'* *,*  *'F'* *,*  *'A'* *, or*  *'K'}* *,* *optional*) – Overrides the memory layout of the result. ‘C’ means C-order,
    ‘F’ means F-order, ‘A’ means ‘F’ if a is Fortran contiguous,
    ‘C’ otherwise. ‘K’ means match the layout of a as closely
    as possible.
* **Returns:**
  **out** – Tensor of fill_value with the same shape and type as a.
* **Return type:**
  Tensor

#### SEE ALSO
[`empty_like`](maxframe.tensor.empty_like.md#maxframe.tensor.empty_like)
: Return an empty tensor with shape and type of input.

`ones_like`
: Return a tensor of ones with shape and type of input.

`zeros_like`
: Return a tensor of zeros with shape and type of input.

[`full`](maxframe.tensor.full.md#maxframe.tensor.full)
: Return a new tensor of given shape filled with value.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> x = mt.arange(6, dtype=int)
>>> mt.full_like(x, 1).execute()
array([1, 1, 1, 1, 1, 1])
>>> mt.full_like(x, 0.1).execute()
array([0, 0, 0, 0, 0, 0])
>>> mt.full_like(x, 0.1, dtype=mt.double).execute()
array([ 0.1,  0.1,  0.1,  0.1,  0.1,  0.1])
>>> mt.full_like(x, mt.nan, dtype=mt.double).execute()
array([ nan,  nan,  nan,  nan,  nan,  nan])
```

```pycon
>>> y = mt.arange(6, dtype=mt.double)
>>> mt.full_like(y, 0.1).execute()
array([ 0.1,  0.1,  0.1,  0.1,  0.1,  0.1])
```
