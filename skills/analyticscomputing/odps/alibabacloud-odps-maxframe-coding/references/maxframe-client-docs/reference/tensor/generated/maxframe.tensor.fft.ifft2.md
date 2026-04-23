# maxframe.tensor.fft.ifft2

### maxframe.tensor.fft.ifft2(a, s=None, axes=(-2, -1), norm=None)

Compute the 2-dimensional inverse discrete Fourier Transform.

This function computes the inverse of the 2-dimensional discrete Fourier
Transform over any number of axes in an M-dimensional array by means of
the Fast Fourier Transform (FFT).  In other words, `ifft2(fft2(a)) == a`
to within numerical accuracy.  By default, the inverse transform is
computed over the last two axes of the input array.

The input, analogously to ifft, should be ordered in the same way as is
returned by fft2, i.e. it should have the term for zero frequency
in the low-order corner of the two axes, the positive frequency terms in
the first half of these axes, the term for the Nyquist frequency in the
middle of the axes and the negative frequency terms in the second half of
both axes, in order of decreasingly negative frequency.

* **Parameters:**
  * **a** (*array_like*) – Input tensor, can be complex.
  * **s** (*sequence* *of* *ints* *,* *optional*) – Shape (length of each axis) of the output (`s[0]` refers to axis 0,
    `s[1]` to axis 1, etc.).  This corresponds to n for `ifft(x, n)`.
    Along each axis, if the given shape is smaller than that of the input,
    the input is cropped.  If it is larger, the input is padded with zeros.
    if s is not given, the shape of the input along the axes specified
    by axes is used.  See notes for issue on ifft zero padding.
  * **axes** (*sequence* *of* *ints* *,* *optional*) – Axes over which to compute the FFT.  If not given, the last two
    axes are used.  A repeated index in axes means the transform over
    that axis is performed multiple times.  A one-element sequence means
    that a one-dimensional FFT is performed.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axes
  indicated by axes, or the last two axes if axes is not given.
* **Return type:**
  complex Tensor
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If s and axes have different length, or axes not given and
        `len(s) != 2`.
  * [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If an element of axes is larger than than the number of axes of a.

#### SEE ALSO
`mt.fft`
: Overall view of discrete Fourier transforms, with definitions and conventions used.

[`fft2`](maxframe.tensor.fft.fft2.md#maxframe.tensor.fft.fft2)
: The forward 2-dimensional FFT, of which ifft2 is the inverse.

[`ifftn`](maxframe.tensor.fft.ifftn.md#maxframe.tensor.fft.ifftn)
: The inverse of the *n*-dimensional FFT.

[`fft`](maxframe.tensor.fft.fft.md#maxframe.tensor.fft.fft)
: The one-dimensional FFT.

[`ifft`](maxframe.tensor.fft.ifft.md#maxframe.tensor.fft.ifft)
: The one-dimensional inverse FFT.

### Notes

ifft2 is just ifftn with a different default for axes.

See ifftn for details and a plotting example, and numpy.fft for
definition and conventions used.

Zero-padding, analogously with ifft, is performed by appending zeros to
the input along the specified dimension.  Although this is the common
approach, it might lead to surprising results.  If another form of zero
padding is desired, it must be performed before ifft2 is called.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = 4 * mt.eye(4)
>>> mt.fft.ifft2(a).execute()
array([[ 1.+0.j,  0.+0.j,  0.+0.j,  0.+0.j],
       [ 0.+0.j,  0.+0.j,  0.+0.j,  1.+0.j],
       [ 0.+0.j,  0.+0.j,  1.+0.j,  0.+0.j],
       [ 0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j]])
```
