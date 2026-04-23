<a id="module-maxframe.tensor.fft"></a>

# Discrete Fourier Transform

## Standard FFTs

| [`maxframe.tensor.fft.fft`](generated/maxframe.tensor.fft.fft.md#maxframe.tensor.fft.fft)       | Compute the one-dimensional discrete Fourier Transform.         |
|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`maxframe.tensor.fft.ifft`](generated/maxframe.tensor.fft.ifft.md#maxframe.tensor.fft.ifft)    | Compute the one-dimensional inverse discrete Fourier Transform. |
| [`maxframe.tensor.fft.fft2`](generated/maxframe.tensor.fft.fft2.md#maxframe.tensor.fft.fft2)    | Compute the 2-dimensional discrete Fourier Transform            |
| [`maxframe.tensor.fft.ifft2`](generated/maxframe.tensor.fft.ifft2.md#maxframe.tensor.fft.ifft2) | Compute the 2-dimensional inverse discrete Fourier Transform.   |
| [`maxframe.tensor.fft.fftn`](generated/maxframe.tensor.fft.fftn.md#maxframe.tensor.fft.fftn)    | Compute the N-dimensional discrete Fourier Transform.           |
| [`maxframe.tensor.fft.ifftn`](generated/maxframe.tensor.fft.ifftn.md#maxframe.tensor.fft.ifftn) | Compute the N-dimensional inverse discrete Fourier Transform.   |

## Real FFTs

| [`maxframe.tensor.fft.rfft`](generated/maxframe.tensor.fft.rfft.md#maxframe.tensor.fft.rfft)       | Compute the one-dimensional discrete Fourier Transform for real input.   |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`maxframe.tensor.fft.irfft`](generated/maxframe.tensor.fft.irfft.md#maxframe.tensor.fft.irfft)    | Compute the inverse of the n-point DFT for real input.                   |
| [`maxframe.tensor.fft.rfft2`](generated/maxframe.tensor.fft.rfft2.md#maxframe.tensor.fft.rfft2)    | Compute the 2-dimensional FFT of a real tensor.                          |
| [`maxframe.tensor.fft.irfft2`](generated/maxframe.tensor.fft.irfft2.md#maxframe.tensor.fft.irfft2) | Compute the 2-dimensional inverse FFT of a real array.                   |
| [`maxframe.tensor.fft.rfftn`](generated/maxframe.tensor.fft.rfftn.md#maxframe.tensor.fft.rfftn)    | Compute the N-dimensional discrete Fourier Transform for real input.     |
| [`maxframe.tensor.fft.irfftn`](generated/maxframe.tensor.fft.irfftn.md#maxframe.tensor.fft.irfftn) | Compute the inverse of the N-dimensional FFT of real input.              |

## Hermitian FFTs

| [`maxframe.tensor.fft.hfft`](generated/maxframe.tensor.fft.hfft.md#maxframe.tensor.fft.hfft)    | Compute the FFT of a signal that has Hermitian symmetry, i.e., a real spectrum.   |
|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`maxframe.tensor.fft.ihfft`](generated/maxframe.tensor.fft.ihfft.md#maxframe.tensor.fft.ihfft) | Compute the inverse FFT of a signal that has Hermitian symmetry.                  |

## Helper routines

| [`maxframe.tensor.fft.fftfreq`](generated/maxframe.tensor.fft.fftfreq.md#maxframe.tensor.fft.fftfreq)       | Return the Discrete Fourier Transform sample frequencies.                              |
|-------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`maxframe.tensor.fft.rfftfreq`](generated/maxframe.tensor.fft.rfftfreq.md#maxframe.tensor.fft.rfftfreq)    | Return the Discrete Fourier Transform sample frequencies (for usage with rfft, irfft). |
| [`maxframe.tensor.fft.fftshift`](generated/maxframe.tensor.fft.fftshift.md#maxframe.tensor.fft.fftshift)    | Shift the zero-frequency component to the center of the spectrum.                      |
| [`maxframe.tensor.fft.ifftshift`](generated/maxframe.tensor.fft.ifftshift.md#maxframe.tensor.fft.ifftshift) | The inverse of fftshift.                                                               |
