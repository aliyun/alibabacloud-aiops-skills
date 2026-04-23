# maxframe.tensor.fft.rfft2

### maxframe.tensor.fft.rfft2(a, s=None, axes=(-2, -1), norm=None)

Compute the 2-dimensional FFT of a real tensor.

* **Parameters:**
  * **a** (*array_like*) – Input tensor, taken to be real.
  * **s** (*sequence* *of* *ints* *,* *optional*) – Shape of the FFT.
  * **axes** (*sequence* *of* *ints* *,* *optional*) – Axes over which to compute the FFT.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The result of the real 2-D FFT.
* **Return type:**
  Tensor

#### SEE ALSO
[`rfftn`](maxframe.tensor.fft.rfftn.md#maxframe.tensor.fft.rfftn)
: Compute the N-dimensional discrete Fourier Transform for real input.

### Notes

This is really just rfftn with different default behavior.
For more details see rfftn.
