# maxframe.tensor.special.gammasgn

### maxframe.tensor.special.gammasgn(x, \*\*kwargs)

Sign of the gamma function.

It is defined as

$$
\text{gammasgn}(x) =
\begin{cases}
  +1 & \Gamma(x) > 0 \\
  -1 & \Gamma(x) < 0
\end{cases}
$$

where $\Gamma$ is the gamma function; see gamma. This
definition is complete since the gamma function is never zero;
see the discussion after [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf).

* **Parameters:**
  * **x** (*array_like*) – Real argument
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Sign of the gamma function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gamma`](maxframe.tensor.special.gamma.md#maxframe.tensor.special.gamma)
: the gamma function

[`gammaln`](maxframe.tensor.special.gammaln.md#maxframe.tensor.special.gammaln)
: log of the absolute value of the gamma function

[`loggamma`](maxframe.tensor.special.loggamma.md#maxframe.tensor.special.loggamma)
: analytic continuation of the log of the gamma function

### Notes

The gamma function can be computed as `gammasgn(x) *
np.exp(gammaln(x))`.

### References
