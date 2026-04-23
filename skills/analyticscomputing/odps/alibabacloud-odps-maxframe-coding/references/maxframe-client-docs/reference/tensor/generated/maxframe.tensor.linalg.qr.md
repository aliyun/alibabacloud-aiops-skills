# maxframe.tensor.linalg.qr

### maxframe.tensor.linalg.qr(a, method='tsqr')

Compute the qr factorization of a matrix.

Factor the matrix a as *qr*, where q is orthonormal and r is
upper-triangular.

* **Parameters:**
  * **a** (*array_like* *,* *shape* *(**M* *,* *N* *)*) – Matrix to be factored.
  * **method** ( *{'tsqr'* *,*  *'sfqr'}* *,* *optional*) – 

    method to calculate qr factorization, tsqr as default

    TSQR is presented in:
    > A. Benson, D. Gleich, and J. Demmel.
    > Direct QR factorizations for tall-and-skinny matrices in
    > MapReduce architectures.
    > IEEE International Conference on Big Data, 2013.
    > [http://arxiv.org/abs/1301.1071](http://arxiv.org/abs/1301.1071)

    FSQR is a QR decomposition for fat and short matrix:
    : A = [A1, A2, A3, …], A1 may be decomposed as A1 = Q1 \* R1,
      for A = Q \* R, Q = Q1, R = [R1, R2, R3, …] where A2 = Q1 \* R2, A3 = Q1 \* R3, …
* **Returns:**
  * **q** (*Tensor of float or complex, optional*) – A matrix with orthonormal columns. When mode = ‘complete’ the
    result is an orthogonal/unitary matrix depending on whether or not
    a is real/complex. The determinant may be either +/- 1 in that
    case.
  * **r** (*Tensor of float or complex, optional*) – The upper-triangular matrix.
* **Raises:**
  **LinAlgError** – If factoring fails.

### Notes

For more information on the qr factorization, see for example:
[http://en.wikipedia.org/wiki/QR_factorization](http://en.wikipedia.org/wiki/QR_factorization)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.random.randn(9, 6)
>>> q, r = mt.linalg.qr(a)
>>> mt.allclose(a, mt.dot(q, r)).execute()  # a does equal qr
True
```
