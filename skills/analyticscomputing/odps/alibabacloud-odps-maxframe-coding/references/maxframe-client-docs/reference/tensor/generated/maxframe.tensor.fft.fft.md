# maxframe.tensor.fft.fft

### maxframe.tensor.fft.fft(a, n=None, axis=-1, norm=None)

Compute the one-dimensional discrete Fourier Transform.

This function computes the one-dimensional *n*-point discrete Fourier
Transform (DFT) with the efficient Fast Fourier Transform (FFT)
algorithm [CT].

* **Parameters:**
  * **a** (*array_like*) – Input tensor, can be complex.
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Length of the transformed axis of the output.
    If n is smaller than the length of the input, the input is cropped.
    If it is larger, the input is padded with zeros.  If n is not given,
    the length of the input along the axis specified by axis is used.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis over which to compute the FFT.  If not given, the last axis is
    used.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axis
  indicated by axis, or the last one if axis is not specified.
* **Return type:**
  complex Tensor
* **Raises:**
  [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – if axes is larger than the last axis of a.

#### SEE ALSO
`mt.fft`
: for definition of the DFT and conventions used.

[`ifft`](maxframe.tensor.fft.ifft.md#maxframe.tensor.fft.ifft)
: The inverse of fft.

[`fft2`](maxframe.tensor.fft.fft2.md#maxframe.tensor.fft.fft2)
: The two-dimensional FFT.

[`fftn`](maxframe.tensor.fft.fftn.md#maxframe.tensor.fft.fftn)
: The *n*-dimensional FFT.

[`rfftn`](maxframe.tensor.fft.rfftn.md#maxframe.tensor.fft.rfftn)
: The *n*-dimensional FFT of real input.

[`fftfreq`](maxframe.tensor.fft.fftfreq.md#maxframe.tensor.fft.fftfreq)
: Frequency bins for given FFT parameters.

### Notes

FFT (Fast Fourier Transform) refers to a way the discrete Fourier
Transform (DFT) can be calculated efficiently, by using symmetries in the
calculated terms.  The symmetry is highest when n is a power of 2, and
the transform is therefore most efficient for these sizes.

The DFT is defined, with the conventions used in this implementation, in
the documentation for the numpy.fft module.

### References

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.fft.fft(mt.exp(2j * mt.pi * mt.arange(8) / 8)).execute()
array([-2.33486982e-16+1.14423775e-17j,  8.00000000e+00-6.89018570e-16j,
        2.33486982e-16+2.33486982e-16j,  0.00000000e+00+0.00000000e+00j,
       -1.14423775e-17+2.33486982e-16j,  0.00000000e+00+1.99159850e-16j,
        1.14423775e-17+1.14423775e-17j,  0.00000000e+00+0.00000000e+00j])
```

In this example, real input has an FFT which is Hermitian, i.e., symmetric
in the real part and anti-symmetric in the imaginary part, as described in
the numpy.fft documentation:

```pycon
>>> import matplotlib.pyplot as plt
>>> t = mt.arange(256)
>>> sp = mt.fft.fft(mt.sin(t))
>>> freq = mt.fft.fftfreq(t.shape[-1])
>>> plt.plot(freq.execute(), sp.real.execute(), freq.execute(), sp.imag.execute())
[<matplotlib.lines.Line2D object at 0x...>, <matplotlib.lines.Line2D object at 0x...>]
>>> plt.show()
```
