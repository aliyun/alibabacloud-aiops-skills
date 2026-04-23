# maxframe.tensor.round_

### maxframe.tensor.round_(a, decimals=0, out=None)

Evenly round to the given number of decimals.

* **Parameters:**
  * **a** (*array_like*) – Input data.
  * **decimals** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of decimal places to round to (default: 0).  If
    decimals is negative, it specifies the number of positions to
    the left of the decimal point.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must have
    the same shape as the expected output, but the type of the output
    values will be cast if necessary.
* **Returns:**
  **rounded_array** – An tensor of the same type as a, containing the rounded values.
  Unless out was specified, a new tensor is created.  A reference to
  the result is returned.

  The real and imaginary parts of complex numbers are rounded
  separately.  The result of rounding a float is a float.
* **Return type:**
  Tensor

#### SEE ALSO
`Tensor.round`
: equivalent method

[`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil), [`fix`](maxframe.tensor.fix.md#maxframe.tensor.fix), [`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor), [`rint`](maxframe.tensor.rint.md#maxframe.tensor.rint), [`trunc`](maxframe.tensor.trunc.md#maxframe.tensor.trunc)

### Notes

For values exactly halfway between rounded decimal values, NumPy
rounds to the nearest even value. Thus 1.5 and 2.5 round to 2.0,
-0.5 and 0.5 round to 0.0, etc. Results may also be surprising due
to the inexact representation of decimal fractions in the IEEE
floating point standard <sup>[1](#id2)</sup> and errors introduced when scaling
by powers of ten.

### References

* <a id='id2'>**[1]**</a> “Lecture Notes on the Status of  IEEE 754”, William Kahan, [http://www.cs.berkeley.edu/~wkahan/ieee754status/IEEE754.PDF](http://www.cs.berkeley.edu/~wkahan/ieee754status/IEEE754.PDF)
* <a id='id3'>**[2]**</a> “How Futile are Mindless Assessments of Roundoff in Floating-Point Computation?”, William Kahan, [http://www.cs.berkeley.edu/~wkahan/Mindless.pdf](http://www.cs.berkeley.edu/~wkahan/Mindless.pdf)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.around([0.37, 1.64]).execute()
array([ 0.,  2.])
>>> mt.around([0.37, 1.64], decimals=1).execute()
array([ 0.4,  1.6])
>>> mt.around([.5, 1.5, 2.5, 3.5, 4.5]).execute() # rounds to nearest even value
array([ 0.,  2.,  2.,  4.,  4.])
>>> mt.around([1,2,3,11], decimals=1).execute() # tensor of ints is returned
array([ 1,  2,  3, 11])
>>> mt.around([1,2,3,11], decimals=-1).execute()
array([ 0,  0,  0, 10])
```
