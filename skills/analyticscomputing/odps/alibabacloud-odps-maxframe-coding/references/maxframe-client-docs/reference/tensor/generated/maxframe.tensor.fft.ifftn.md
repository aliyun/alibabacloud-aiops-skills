# maxframe.tensor.fft.ifftn

### maxframe.tensor.fft.ifftn(a, s=None, axes=None, norm=None)

Compute the N-dimensional inverse discrete Fourier Transform.

This function computes the inverse of the N-dimensional discrete
Fourier Transform over any number of axes in an M-dimensional tensor by
means of the Fast Fourier Transform (FFT).  In other words,
`ifftn(fftn(a)) == a` to within numerical accuracy.
For a description of the definitions and conventions used, see mt.fft.

The input, analogously to ifft, should be ordered in the same way as is
returned by fftn, i.e. it should have the term for zero frequency
in all axes in the low-order corner, the positive frequency terms in the
first half of all axes, the term for the Nyquist frequency in the middle
of all axes and the negative frequency terms in the second half of all
axes, in order of decreasingly negative frequency.

* **Parameters:**
  * **a** (*array_like*) – Input tensor, can be complex.
  * **s** (*sequence* *of* *ints* *,* *optional*) – Shape (length of each transformed axis) of the output
    (`s[0]` refers to axis 0, `s[1]` to axis 1, etc.).
    This corresponds to `n` for `ifft(x, n)`.
    Along any axis, if the given shape is smaller than that of the input,
    the input is cropped.  If it is larger, the input is padded with zeros.
    if s is not given, the shape of the input along the axes specified
    by axes is used.  See notes for issue on ifft zero padding.
  * **axes** (*sequence* *of* *ints* *,* *optional*) – Axes over which to compute the IFFT.  If not given, the last `len(s)`
    axes are used, or all axes if s is also not specified.
    Repeated indices in axes means that the inverse transform over that
    axis is performed multiple times.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axes
  indicated by axes, or by a combination of s or a,
  as explained in the parameters section above.
* **Return type:**
  complex Tensor
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If s and axes have different length.
  * [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If an element of axes is larger than than the number of axes of a.

#### SEE ALSO
`mt.fft`
: Overall view of discrete Fourier transforms, with definitions and conventions used.

[`fftn`](maxframe.tensor.fft.fftn.md#maxframe.tensor.fft.fftn)
: The forward *n*-dimensional FFT, of which ifftn is the inverse.

[`ifft`](maxframe.tensor.fft.ifft.md#maxframe.tensor.fft.ifft)
: The one-dimensional inverse FFT.

[`ifft2`](maxframe.tensor.fft.ifft2.md#maxframe.tensor.fft.ifft2)
: The two-dimensional inverse FFT.

[`ifftshift`](maxframe.tensor.fft.ifftshift.md#maxframe.tensor.fft.ifftshift)
: Undoes fftshift, shifts zero-frequency terms to beginning of tensor.

### Notes

See mt.fft for definitions and conventions used.

Zero-padding, analogously with ifft, is performed by appending zeros to
the input along the specified dimension.  Although this is the common
approach, it might lead to surprising results.  If another form of zero
padding is desired, it must be performed before ifftn is called.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.eye(4)
>>> mt.fft.ifftn(mt.fft.fftn(a, axes=(0,)), axes=(1,)).execute()
array([[ 1.+0.j,  0.+0.j,  0.+0.j,  0.+0.j],
       [ 0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j],
       [ 0.+0.j,  0.+0.j,  1.+0.j,  0.+0.j],
       [ 0.+0.j,  0.+0.j,  0.+0.j,  1.+0.j]])
```

Create and plot an image with band-limited frequency content:

```pycon
>>> import matplotlib.pyplot as plt
>>> n = mt.zeros((200,200), dtype=complex)
>>> n[60:80, 20:40] = mt.exp(1j*mt.random.uniform(0, 2*mt.pi, (20, 20)))
>>> im = mt.fft.ifftn(n).real
>>> plt.imshow(im.execute())
<matplotlib.image.AxesImage object at 0x...>
>>> plt.show()
```
