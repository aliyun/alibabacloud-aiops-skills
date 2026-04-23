# maxframe.tensor.nan_to_num

### maxframe.tensor.nan_to_num(x, copy=True, \*\*kwargs)

Replace nan with zero and inf with large finite numbers.

If x is inexact, NaN is replaced by zero, and infinity and -infinity
replaced by the respectively largest and most negative finite floating
point values representable by `x.dtype`.

For complex dtypes, the above is applied to each of the real and
imaginary components of x separately.

If x is not inexact, then no replacements are made.

* **Parameters:**
  * **x** (*array_like*) – Input data.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Whether to create a copy of x (True) or to replace values
    in-place (False). The in-place operation only occurs if
    casting to an array does not require a copy.
    Default is True.
* **Returns:**
  **out** – x, with the non-finite values replaced. If copy is False, this may
  be x itself.
* **Return type:**
  Tensor

#### SEE ALSO
[`isinf`](maxframe.tensor.isinf.md#maxframe.tensor.isinf)
: Shows which elements are positive or negative infinity.

`isneginf`
: Shows which elements are negative infinity.

`isposinf`
: Shows which elements are positive infinity.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Shows which elements are Not a Number (NaN).

[`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)
: Shows which elements are finite (not NaN, not infinity)

### Notes

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754). This means that Not a Number is not equivalent to infinity.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([mt.inf, -mt.inf, mt.nan, -128, 128])
>>> mt.nan_to_num(x).execute()
array([  1.79769313e+308,  -1.79769313e+308,   0.00000000e+000,
        -1.28000000e+002,   1.28000000e+002])
>>> y = mt.array([complex(mt.inf, mt.nan), mt.nan, complex(mt.nan, mt.inf)])
>>> mt.nan_to_num(y).execute()
array([  1.79769313e+308 +0.00000000e+000j,
         0.00000000e+000 +0.00000000e+000j,
         0.00000000e+000 +1.79769313e+308j])
```
