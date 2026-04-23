# Mathematical Functions

## Trigonometric functions

| [`maxframe.tensor.sin`](generated/maxframe.tensor.sin.md#maxframe.tensor.sin)             | Trigonometric sine, element-wise.                                    |
|-------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`maxframe.tensor.cos`](generated/maxframe.tensor.cos.md#maxframe.tensor.cos)             | Cosine element-wise.                                                 |
| [`maxframe.tensor.tan`](generated/maxframe.tensor.tan.md#maxframe.tensor.tan)             | Compute tangent element-wise.                                        |
| [`maxframe.tensor.arcsin`](generated/maxframe.tensor.arcsin.md#maxframe.tensor.arcsin)    | Inverse sine, element-wise.                                          |
| [`maxframe.tensor.arccos`](generated/maxframe.tensor.arccos.md#maxframe.tensor.arccos)    | Trigonometric inverse cosine, element-wise.                          |
| [`maxframe.tensor.arctan`](generated/maxframe.tensor.arctan.md#maxframe.tensor.arctan)    | Trigonometric inverse tangent, element-wise.                         |
| [`maxframe.tensor.hypot`](generated/maxframe.tensor.hypot.md#maxframe.tensor.hypot)       | Given the "legs" of a right triangle, return its hypotenuse.         |
| [`maxframe.tensor.arctan2`](generated/maxframe.tensor.arctan2.md#maxframe.tensor.arctan2) | Element-wise arc tangent of `x1/x2` choosing the quadrant correctly. |
| [`maxframe.tensor.degrees`](generated/maxframe.tensor.degrees.md#maxframe.tensor.degrees) | Convert angles from radians to degrees.                              |
| [`maxframe.tensor.radians`](generated/maxframe.tensor.radians.md#maxframe.tensor.radians) | Convert angles from degrees to radians.                              |
| [`maxframe.tensor.deg2rad`](generated/maxframe.tensor.deg2rad.md#maxframe.tensor.deg2rad) | Convert angles from degrees to radians.                              |
| [`maxframe.tensor.rad2deg`](generated/maxframe.tensor.rad2deg.md#maxframe.tensor.rad2deg) | Convert angles from radians to degrees.                              |

## Hyperbolic functions

| [`maxframe.tensor.sinh`](generated/maxframe.tensor.sinh.md#maxframe.tensor.sinh)          | Hyperbolic sine, element-wise.           |
|-------------------------------------------------------------------------------------------|------------------------------------------|
| [`maxframe.tensor.cosh`](generated/maxframe.tensor.cosh.md#maxframe.tensor.cosh)          | Hyperbolic cosine, element-wise.         |
| [`maxframe.tensor.tanh`](generated/maxframe.tensor.tanh.md#maxframe.tensor.tanh)          | Compute hyperbolic tangent element-wise. |
| [`maxframe.tensor.arcsinh`](generated/maxframe.tensor.arcsinh.md#maxframe.tensor.arcsinh) | Inverse hyperbolic sine element-wise.    |
| [`maxframe.tensor.arccosh`](generated/maxframe.tensor.arccosh.md#maxframe.tensor.arccosh) | Inverse hyperbolic cosine, element-wise. |
| [`maxframe.tensor.arctanh`](generated/maxframe.tensor.arctanh.md#maxframe.tensor.arctanh) | Inverse hyperbolic tangent element-wise. |

## Rounding

| [`maxframe.tensor.around`](generated/maxframe.tensor.around.md#maxframe.tensor.around)   | Evenly round to the given number of decimals.          |
|------------------------------------------------------------------------------------------|--------------------------------------------------------|
| [`maxframe.tensor.round_`](generated/maxframe.tensor.round_.md#maxframe.tensor.round_)   | Evenly round to the given number of decimals.          |
| [`maxframe.tensor.rint`](generated/maxframe.tensor.rint.md#maxframe.tensor.rint)         | Round elements of the tensor to the nearest integer.   |
| [`maxframe.tensor.fix`](generated/maxframe.tensor.fix.md#maxframe.tensor.fix)            | Round to nearest integer towards zero.                 |
| [`maxframe.tensor.floor`](generated/maxframe.tensor.floor.md#maxframe.tensor.floor)      | Return the floor of the input, element-wise.           |
| [`maxframe.tensor.ceil`](generated/maxframe.tensor.ceil.md#maxframe.tensor.ceil)         | Return the ceiling of the input, element-wise.         |
| [`maxframe.tensor.trunc`](generated/maxframe.tensor.trunc.md#maxframe.tensor.trunc)      | Return the truncated value of the input, element-wise. |

## Sums, products, differences

| [`maxframe.tensor.prod`](generated/maxframe.tensor.prod.md#maxframe.tensor.prod)                   | Return the product of tensor elements over a given axis.                                                 |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| [`maxframe.tensor.sum`](generated/maxframe.tensor.sum.md#maxframe.tensor.sum)                      | Sum of tensor elements over a given axis.                                                                |
| [`maxframe.tensor.nanprod`](generated/maxframe.tensor.nanprod.md#maxframe.tensor.nanprod)          | Return the product of array elements over a given axis treating Not a Numbers (NaNs) as ones.            |
| [`maxframe.tensor.nansum`](generated/maxframe.tensor.nansum.md#maxframe.tensor.nansum)             | Return the sum of array elements over a given axis treating Not a Numbers (NaNs) as zero.                |
| [`maxframe.tensor.cumprod`](generated/maxframe.tensor.cumprod.md#maxframe.tensor.cumprod)          | Return the cumulative product of elements along a given axis.                                            |
| [`maxframe.tensor.cumsum`](generated/maxframe.tensor.cumsum.md#maxframe.tensor.cumsum)             | Return the cumulative sum of the elements along a given axis.                                            |
| [`maxframe.tensor.nancumprod`](generated/maxframe.tensor.nancumprod.md#maxframe.tensor.nancumprod) | Return the cumulative product of tensor elements over a given axis treating Not a Numbers (NaNs) as one. |
| [`maxframe.tensor.nancumsum`](generated/maxframe.tensor.nancumsum.md#maxframe.tensor.nancumsum)    | Return the cumulative sum of tensor elements over a given axis treating Not a Numbers (NaNs) as zero.    |
| [`maxframe.tensor.diff`](generated/maxframe.tensor.diff.md#maxframe.tensor.diff)                   | Calculate the n-th discrete difference along the given axis.                                             |
| [`maxframe.tensor.ediff1d`](generated/maxframe.tensor.ediff1d.md#maxframe.tensor.ediff1d)          | The differences between consecutive elements of a tensor.                                                |
| [`maxframe.tensor.trapezoid`](generated/maxframe.tensor.trapezoid.md#maxframe.tensor.trapezoid)    | Integrate along the given axis using the composite trapezoidal rule.                                     |

## Exponential and logarithms

| [`maxframe.tensor.exp`](generated/maxframe.tensor.exp.md#maxframe.tensor.exp)                      | Calculate the exponential of all elements in the input tensor.           |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`maxframe.tensor.expm1`](generated/maxframe.tensor.expm1.md#maxframe.tensor.expm1)                | Calculate `exp(x) - 1` for all elements in the tensor.                   |
| [`maxframe.tensor.exp2`](generated/maxframe.tensor.exp2.md#maxframe.tensor.exp2)                   | Calculate 2\*\*p for all p in the input tensor.                          |
| [`maxframe.tensor.log`](generated/maxframe.tensor.log.md#maxframe.tensor.log)                      | Natural logarithm, element-wise.                                         |
| [`maxframe.tensor.log10`](generated/maxframe.tensor.log10.md#maxframe.tensor.log10)                | Return the base 10 logarithm of the input tensor, element-wise.          |
| [`maxframe.tensor.log2`](generated/maxframe.tensor.log2.md#maxframe.tensor.log2)                   | Base-2 logarithm of x.                                                   |
| [`maxframe.tensor.log1p`](generated/maxframe.tensor.log1p.md#maxframe.tensor.log1p)                | Return the natural logarithm of one plus the input tensor, element-wise. |
| [`maxframe.tensor.logaddexp`](generated/maxframe.tensor.logaddexp.md#maxframe.tensor.logaddexp)    | Logarithm of the sum of exponentiations of the inputs.                   |
| [`maxframe.tensor.logaddexp2`](generated/maxframe.tensor.logaddexp2.md#maxframe.tensor.logaddexp2) | Logarithm of the sum of exponentiations of the inputs in base-2.         |

## Other special functions

| [`maxframe.tensor.i0`](generated/maxframe.tensor.i0.md#maxframe.tensor.i0)       | Modified Bessel function of the first kind, order 0.   |
|----------------------------------------------------------------------------------|--------------------------------------------------------|
| [`maxframe.tensor.sinc`](generated/maxframe.tensor.sinc.md#maxframe.tensor.sinc) | Return the sinc function.                              |

## Floating point routines

| [`maxframe.tensor.signbit`](generated/maxframe.tensor.signbit.md#maxframe.tensor.signbit)       | Returns element-wise True where signbit is set (less than zero).        |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`maxframe.tensor.copysign`](generated/maxframe.tensor.copysign.md#maxframe.tensor.copysign)    | Change the sign of x1 to that of x2, element-wise.                      |
| [`maxframe.tensor.frexp`](generated/maxframe.tensor.frexp.md#maxframe.tensor.frexp)             | Decompose the elements of x into mantissa and twos exponent.            |
| [`maxframe.tensor.ldexp`](generated/maxframe.tensor.ldexp.md#maxframe.tensor.ldexp)             | Returns x1 \* 2\*\*x2, element-wise.                                    |
| [`maxframe.tensor.nextafter`](generated/maxframe.tensor.nextafter.md#maxframe.tensor.nextafter) | Return the next floating-point value after x1 towards x2, element-wise. |
| [`maxframe.tensor.spacing`](generated/maxframe.tensor.spacing.md#maxframe.tensor.spacing)       | Return the distance between x and the nearest adjacent number.          |

## Arithmetic operations

| [`maxframe.tensor.add`](generated/maxframe.tensor.add.md#maxframe.tensor.add)                            | Add arguments element-wise.                                                |
|----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`maxframe.tensor.reciprocal`](generated/maxframe.tensor.reciprocal.md#maxframe.tensor.reciprocal)       | Return the reciprocal of the argument, element-wise.                       |
| [`maxframe.tensor.positive`](generated/maxframe.tensor.positive.md#maxframe.tensor.positive)             | Numerical positive, element-wise.                                          |
| [`maxframe.tensor.negative`](generated/maxframe.tensor.negative.md#maxframe.tensor.negative)             | Numerical negative, element-wise.                                          |
| [`maxframe.tensor.multiply`](generated/maxframe.tensor.multiply.md#maxframe.tensor.multiply)             | Multiply arguments element-wise.                                           |
| [`maxframe.tensor.divide`](generated/maxframe.tensor.divide.md#maxframe.tensor.divide)                   | Divide arguments element-wise.                                             |
| [`maxframe.tensor.power`](generated/maxframe.tensor.power.md#maxframe.tensor.power)                      | First tensor elements raised to powers from second tensor, element-wise.   |
| [`maxframe.tensor.subtract`](generated/maxframe.tensor.subtract.md#maxframe.tensor.subtract)             | Subtract arguments, element-wise.                                          |
| [`maxframe.tensor.true_divide`](generated/maxframe.tensor.true_divide.md#maxframe.tensor.true_divide)    | Returns a true division of the inputs, element-wise.                       |
| [`maxframe.tensor.floor_divide`](generated/maxframe.tensor.floor_divide.md#maxframe.tensor.floor_divide) | Return the largest integer smaller or equal to the division of the inputs. |
| [`maxframe.tensor.float_power`](generated/maxframe.tensor.float_power.md#maxframe.tensor.float_power)    | First tensor elements raised to powers from second array, element-wise.    |
| [`maxframe.tensor.fmod`](generated/maxframe.tensor.fmod.md#maxframe.tensor.fmod)                         | Return the element-wise remainder of division.                             |
| [`maxframe.tensor.mod`](generated/maxframe.tensor.mod.md#maxframe.tensor.mod)                            | Return element-wise remainder of division.                                 |
| [`maxframe.tensor.modf`](generated/maxframe.tensor.modf.md#maxframe.tensor.modf)                         | Return the fractional and integral parts of a tensor, element-wise.        |
| [`maxframe.tensor.remainder`](generated/maxframe.tensor.remainder.md#maxframe.tensor.remainder)          | Return element-wise remainder of division.                                 |

## Handling complex numbers

| [`maxframe.tensor.angle`](generated/maxframe.tensor.angle.md#maxframe.tensor.angle)   | Return the angle of the complex argument.          |
|---------------------------------------------------------------------------------------|----------------------------------------------------|
| [`maxframe.tensor.real`](generated/maxframe.tensor.real.md#maxframe.tensor.real)      | Return the real part of the complex argument.      |
| [`maxframe.tensor.imag`](generated/maxframe.tensor.imag.md#maxframe.tensor.imag)      | Return the imaginary part of the complex argument. |
| [`maxframe.tensor.conj`](generated/maxframe.tensor.conj.md#maxframe.tensor.conj)      | Return the complex conjugate, element-wise.        |

## Miscellaneous

| [`maxframe.tensor.sqrt`](generated/maxframe.tensor.sqrt.md#maxframe.tensor.sqrt)                   | Return the positive square-root of an tensor, element-wise.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`maxframe.tensor.cbrt`](generated/maxframe.tensor.cbrt.md#maxframe.tensor.cbrt)                   | Return the cube-root of an tensor, element-wise.              |
| [`maxframe.tensor.square`](generated/maxframe.tensor.square.md#maxframe.tensor.square)             | Return the element-wise square of the input.                  |
| [`maxframe.tensor.absolute`](generated/maxframe.tensor.absolute.md#maxframe.tensor.absolute)       | Calculate the absolute value element-wise.                    |
| [`maxframe.tensor.sign`](generated/maxframe.tensor.sign.md#maxframe.tensor.sign)                   | Returns an element-wise indication of the sign of a number.   |
| [`maxframe.tensor.maximum`](generated/maxframe.tensor.maximum.md#maxframe.tensor.maximum)          | Element-wise maximum of tensor elements.                      |
| [`maxframe.tensor.minimum`](generated/maxframe.tensor.minimum.md#maxframe.tensor.minimum)          | Element-wise minimum of tensor elements.                      |
| [`maxframe.tensor.fmax`](generated/maxframe.tensor.fmax.md#maxframe.tensor.fmax)                   | Element-wise maximum of array elements.                       |
| [`maxframe.tensor.fmin`](generated/maxframe.tensor.fmin.md#maxframe.tensor.fmin)                   | Element-wise minimum of array elements.                       |
| [`maxframe.tensor.nan_to_num`](generated/maxframe.tensor.nan_to_num.md#maxframe.tensor.nan_to_num) | Replace nan with zero and inf with large finite numbers.      |
