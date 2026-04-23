# maxframe.tensor.sin

### maxframe.tensor.sin(x, out=None, where=None, \*\*kwargs)

Trigonometric sine, element-wise.

* **Parameters:**
  * **x** (*array_like*) – Angle, in radians ($2 \pi$ rad equals 360 degrees).
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The sine of each element of x.
* **Return type:**
  array_like

#### SEE ALSO
[`arcsin`](maxframe.tensor.arcsin.md#maxframe.tensor.arcsin), [`sinh`](maxframe.tensor.sinh.md#maxframe.tensor.sinh), [`cos`](maxframe.tensor.cos.md#maxframe.tensor.cos)

### Notes

The sine is one of the fundamental functions of trigonometry (the
mathematical study of triangles).  Consider a circle of radius 1
centered on the origin.  A ray comes in from the $+x$ axis, makes
an angle at the origin (measured counter-clockwise from that axis), and
departs from the origin.  The $y$ coordinate of the outgoing
ray’s intersection with the unit circle is the sine of that angle.  It
ranges from -1 for $x=3\pi / 2$ to +1 for $\pi / 2.$  The
function has zeroes where the angle is a multiple of $\pi$.
Sines of angles between $\pi$ and $2\pi$ are negative.
The numerous properties of the sine and related functions are included
in any standard trigonometry text.

### Examples

Print sine of one angle:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.sin(mt.pi/2.).execute()
1.0
```

Print sines of an array of angles given in degrees:

```pycon
>>> mt.sin(mt.array((0., 30., 45., 60., 90.)) * mt.pi / 180. ).execute()
array([ 0.        ,  0.5       ,  0.70710678,  0.8660254 ,  1.        ])
```

Plot the sine function:

```pycon
>>> import matplotlib.pylab as plt
>>> x = mt.linspace(-mt.pi, mt.pi, 201)
>>> plt.plot(x.execute(), mt.sin(x).execute())
>>> plt.xlabel('Angle [rad]')
>>> plt.ylabel('sin(x)')
>>> plt.axis('tight')
>>> plt.show()
```
