# maxframe.tensor.fft.fftn

### maxframe.tensor.fft.fftn(a, s=None, axes=None, norm=None)

Compute the N-dimensional discrete Fourier Transform.

This function computes the *N*-dimensional discrete Fourier Transform over
any number of axes in an *M*-dimensional tensor by means of the Fast Fourier
Transform (FFT).

* **Parameters:**
  * **a** (*array_like*) – Input tensor, can be complex.
  * **s** (*sequence* *of* *ints* *,* *optional*) – Shape (length of each transformed axis) of the output
    (`s[0]` refers to axis 0, `s[1]` to axis 1, etc.).
    This corresponds to `n` for `fft(x, n)`.
    Along any axis, if the given shape is smaller than that of the input,
    the input is cropped.  If it is larger, the input is padded with zeros.
    if s is not given, the shape of the input along the axes specified
    by axes is used.
  * **axes** (*sequence* *of* *ints* *,* *optional*) – Axes over which to compute the FFT.  If not given, the last `len(s)`
    axes are used, or all axes if s is also not specified.
    Repeated indices in axes means that the transform over that axis is
    performed multiple times.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axes
  indicated by axes, or by a combination of s and a,
  as explained in the parameters section above.
* **Return type:**
  complex Tensor
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If s and axes have different length.
  * [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If an element of axes is larger than than the number of axes of a.

#### SEE ALSO
`mt.fft`
: Overall view of discrete Fourier transforms, with definitions and conventions used.

[`ifftn`](maxframe.tensor.fft.ifftn.md#maxframe.tensor.fft.ifftn)
: The inverse of fftn, the inverse *n*-dimensional FFT.

[`fft`](maxframe.tensor.fft.fft.md#maxframe.tensor.fft.fft)
: The one-dimensional FFT, with definitions and conventions used.

[`rfftn`](maxframe.tensor.fft.rfftn.md#maxframe.tensor.fft.rfftn)
: The *n*-dimensional FFT of real input.

[`fft2`](maxframe.tensor.fft.fft2.md#maxframe.tensor.fft.fft2)
: The two-dimensional FFT.

[`fftshift`](maxframe.tensor.fft.fftshift.md#maxframe.tensor.fft.fftshift)
: Shifts zero-frequency terms to centre of tensor

### Notes

The output, analogously to fft, contains the term for zero frequency in
the low-order corner of all axes, the positive frequency terms in the
first half of all axes, the term for the Nyquist frequency in the middle
of all axes and the negative frequency terms in the second half of all
axes, in order of decreasingly negative frequency.

See mt.fft for details, definitions and conventions used.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.mgrid[:3, :3, :3][0]
>>> mt.fft.fftn(a, axes=(1, 2)).execute()
array([[[  0.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j]],
       [[  9.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j]],
       [[ 18.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j],
        [  0.+0.j,   0.+0.j,   0.+0.j]]])
>>> mt.fft.fftn(a, (2, 2), axes=(0, 1)).execute()
array([[[ 2.+0.j,  2.+0.j,  2.+0.j],
        [ 0.+0.j,  0.+0.j,  0.+0.j]],
       [[-2.+0.j, -2.+0.j, -2.+0.j],
        [ 0.+0.j,  0.+0.j,  0.+0.j]]])
```

```pycon
>>> import matplotlib.pyplot as plt
>>> [X, Y] = mt.meshgrid(2 * mt.pi * mt.arange(200) / 12,
...                      2 * mt.pi * mt.arange(200) / 34)
>>> S = mt.sin(X) + mt.cos(Y) + mt.random.uniform(0, 1, X.shape)
>>> FS = mt.fft.fftn(S)
>>> plt.imshow(mt.log(mt.abs(mt.fft.fftshift(FS))**2).execute())
<matplotlib.image.AxesImage object at 0x...>
>>> plt.show()
```
