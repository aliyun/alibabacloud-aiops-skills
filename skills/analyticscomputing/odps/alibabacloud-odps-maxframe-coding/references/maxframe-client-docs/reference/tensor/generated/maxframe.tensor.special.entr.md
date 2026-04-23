# maxframe.tensor.special.entr

### maxframe.tensor.special.entr(x, out=None, where=None, \*\*kwargs)

Elementwise function for computing entropy.

$$
\text{entr}(x) = \begin{cases} - x \log(x) & x > 0  \\ 0 & x = 0 \\ -\infty & \text{otherwise} \end{cases}

$$

* **Parameters:**
  **x** (*Tensor*) – Input tensor.
* **Returns:**
  **res** – The value of the elementwise entropy function at the given points x.
* **Return type:**
  Tensor

#### SEE ALSO
`kl_div`, [`rel_entr`](maxframe.tensor.special.rel_entr.md#maxframe.tensor.special.rel_entr)

### Notes

This function is concave.
