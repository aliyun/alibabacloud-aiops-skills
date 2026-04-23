# maxframe.tensor.empty_like

### maxframe.tensor.empty_like(a, dtype=None, gpu=None, order='K')

Return a new tensor with the same shape and type as a given tensor.

* **Parameters:**
  * **a** (*array_like*) – The shape and data-type of a define these same attributes of the
    returned tensor.
  * **dtype** (*data-type* *,* *optional*) – Overrides the data type of the result.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, None as default
  * **order** ( *{'C'* *,*  *'F'* *,*  *'A'* *, or*  *'K'}* *,* *optional*) – Overrides the memory layout of the result. ‘C’ means C-order,
    ‘F’ means F-order, ‘A’ means ‘F’ if `prototype` is Fortran
    contiguous, ‘C’ otherwise. ‘K’ means match the layout of `prototype`
    as closely as possible.
* **Returns:**
  **out** – Array of uninitialized (arbitrary) data with the same
  shape and type as a.
* **Return type:**
  Tensor

#### SEE ALSO
`ones_like`
: Return a tensor of ones with shape and type of input.

`zeros_like`
: Return a tensor of zeros with shape and type of input.

[`empty`](maxframe.tensor.empty.md#maxframe.tensor.empty)
: Return a new uninitialized tensor.

[`ones`](maxframe.tensor.ones.md#maxframe.tensor.ones)
: Return a new tensor setting values to one.

[`zeros`](maxframe.tensor.zeros.md#maxframe.tensor.zeros)
: Return a new tensor setting values to zero.

### Notes

This function does *not* initialize the returned tensor; to do that use
zeros_like or ones_like instead.  It may be marginally faster than
the functions that do set the array values.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = ([1,2,3], [4,5,6])                         # a is array-like
>>> mt.empty_like(a).execute()
array([[-1073741821, -1073741821,           3],    #ranm
       [          0,           0, -1073741821]])
>>> a = mt.array([[1., 2., 3.],[4.,5.,6.]])
>>> mt.empty_like(a).execute()
array([[ -2.00000715e+000,   1.48219694e-323,  -2.00000572e+000],#random
       [  4.38791518e-305,  -2.00000715e+000,   4.17269252e-309]])
```
