# maxframe.tensor.special.rel_entr

### maxframe.tensor.special.rel_entr(x, y, out=None, where=None, \*\*kwargs)

Elementwise function for computing relative entropy.

$$
\mathrm{rel\_entr}(x, y) =
    \begin{cases}
        x \log(x / y) & x > 0, y > 0 \\
        0 & x = 0, y \ge 0 \\
        \infty & \text{otherwise}
    \end{cases}
$$

* **Parameters:**
  * **x** (*array_like*) – Input arrays
  * **y** (*array_like*) – Input arrays
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  Relative entropy of the inputs
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`entr`](maxframe.tensor.special.entr.md#maxframe.tensor.special.entr), `kl_div`

### Notes

This function is jointly convex in x and y.

The origin of this function is in convex programming; see
<sup>[1](#id3)</sup>. Given two discrete probability distributions $p_1,
\ldots, p_n$ and $q_1, \ldots, q_n$, to get the relative
entropy of statistics compute the sum

$$
\sum_{i = 1}^n \mathrm{rel\_entr}(p_i, q_i).
$$

See <sup>[2](#id4)</sup> for details.

### References

* <a id='id3'>**[1]**</a> Grant, Boyd, and Ye, “CVX: Matlab Software for Disciplined Convex Programming”, [http://cvxr.com/cvx/](http://cvxr.com/cvx/)
* <a id='id4'>**[2]**</a> Kullback-Leibler divergence, [https://en.wikipedia.org/wiki/Kullback%E2%80%93Leibler_divergence](https://en.wikipedia.org/wiki/Kullback%E2%80%93Leibler_divergence)
