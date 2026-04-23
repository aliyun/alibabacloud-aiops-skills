# maxframe.tensor.special.ellip_harm

### maxframe.tensor.special.ellip_harm(h2, k2, n, p, s, signm=1, signn=1, \*\*kwargs)

Ellipsoidal harmonic functions E^p_n(l)

These are also known as Lame functions of the first kind, and are
solutions to the Lame equation:

$$
(s^2 - h^2)(s^2 - k^2)E''(s)
+ s(2s^2 - h^2 - k^2)E'(s) + (a - q s^2)E(s) = 0

$$

where $q = (n+1)n$ and $a$ is the eigenvalue (not
returned) corresponding to the solutions.

* **Parameters:**
  * **h2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `h**2`
  * **k2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `k**2`; should be larger than `h**2`
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Degree
  * **s** ([*float*](https://docs.python.org/3/library/functions.html#float)) – Coordinate
  * **p** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Order, can range between [1,2n+1]
  * **signm** ( *{1* *,*  *-1}* *,* *optional*) – Sign of prefactor of functions. Can be +/-1. See Notes.
  * **signn** ( *{1* *,*  *-1}* *,* *optional*) – Sign of prefactor of functions. Can be +/-1. See Notes.
* **Returns:**
  **E** – the harmonic $E^p_n(s)$
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`ellip_harm_2`](maxframe.tensor.special.ellip_harm_2.md#maxframe.tensor.special.ellip_harm_2), [`ellip_normal`](maxframe.tensor.special.ellip_normal.md#maxframe.tensor.special.ellip_normal)

### Notes

The geometric interpretation of the ellipsoidal functions is
explained in <sup>[2](#id5)</sup>, <sup>[3](#id8)</sup>, <sup>[4](#id9)</sup>. The signm and signn arguments control the
sign of prefactors for functions according to their type:

```default
K : +1
L : signm
M : signn
N : signm*signn
```

### References

* <a id='id4'>**[1]**</a> Digital Library of Mathematical Functions 29.12 [https://dlmf.nist.gov/29.12](https://dlmf.nist.gov/29.12)
* <a id='id5'>**[2]**</a> Bardhan and Knepley, “Computational science and re-discovery: open-source implementations of ellipsoidal harmonics for problems in potential theory”, Comput. Sci. Disc. 5, 014006 (2012)  ``` :doi:`10.1088/1749-4699/5/1/014006` ```  .
* <a id='id8'>**[3]**</a> David J.and Dechambre P, “Computation of Ellipsoidal Gravity Field Harmonics for small solar system bodies” pp. 30-36, 2000
* <a id='id9'>**[4]**</a> George Dassios, “Ellipsoidal Harmonics: Theory and Applications” pp. 418, 2012
