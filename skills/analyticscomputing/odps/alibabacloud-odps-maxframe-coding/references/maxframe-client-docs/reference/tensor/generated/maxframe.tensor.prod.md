# maxframe.tensor.prod

### maxframe.tensor.prod(a, axis=None, dtype=None, out=None, keepdims=None)

Return the product of tensor elements over a given axis.

* **Parameters:**
  * **a** (*array_like*) – Input data.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which a product is performed.  The default,
    axis=None, will calculate the product of all the elements in the
    input tensor. If axis is negative it counts from the last to the
    first axis.

    If axis is a tuple of ints, a product is performed on all of the
    axes specified in the tuple instead of a single axis or all the
    axes as before.
  * **dtype** (*dtype* *,* *optional*) – The type of the returned tensor, as well as of the accumulator in
    which the elements are multiplied.  The dtype of a is used by
    default unless a has an integer dtype of less precision than the
    default platform integer.  In that case, if a is signed then the
    platform integer is used while if a is unsigned then an unsigned
    integer of the same precision as the platform integer is used.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must have
    the same shape as the expected output, but the type of the output
    values will be cast if necessary.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left in the
    result as dimensions with size one. With this option, the result
    will broadcast correctly against the input array.

    If the default value is passed, then keepdims will not be
    passed through to the prod method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **product_along_axis** – An tensor shaped as a but with the specified axis removed.
  Returns a reference to out if specified.
* **Return type:**
  Tensor, see dtype parameter above.

#### SEE ALSO
`Tensor.prod`
: equivalent method

### Notes

Arithmetic is modular when using integer types, and no error is
raised on overflow.  That means that, on a 32-bit platform:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([536870910, 536870910, 536870910, 536870910])
>>> mt.prod(x).execute()  # random
16
```

The product of an empty array is the neutral element 1:

```pycon
>>> mt.prod([]).execute()
1.0
```

### Examples

By default, calculate the product of all elements:

```pycon
>>> mt.prod([1.,2.]).execute()
2.0
```

Even when the input array is two-dimensional:

```pycon
>>> mt.prod([[1.,2.],[3.,4.]]).execute()
24.0
```

But we can also specify the axis over which to multiply:

```pycon
>>> mt.prod([[1.,2.],[3.,4.]], axis=1).execute()
array([  2.,  12.])
```

If the type of x is unsigned, then the output type is
the unsigned platform integer:

```pycon
>>> x = mt.array([1, 2, 3], dtype=mt.uint8)
>>> mt.prod(x).dtype == mt.uint
True
```

If x is of a signed integer type, then the output type
is the default platform integer:

```pycon
>>> x = mt.array([1, 2, 3], dtype=mt.int8)
>>> mt.prod(x).dtype == int
True
```
