# maxframe.tensor.tensordot

### maxframe.tensor.tensordot(a, b, axes=2, sparse=None)

Compute tensor dot product along specified axes for tensors >= 1-D.

Given two tensors (arrays of dimension greater than or equal to one),
a and b, and an array_like object containing two array_like
objects, `(a_axes, b_axes)`, sum the products of a’s and b’s
elements (components) over the axes specified by `a_axes` and
`b_axes`. The third argument can be a single non-negative
integer_like scalar, `N`; if it is such, then the last `N`
dimensions of a and the first `N` dimensions of b are summed
over.

* **Parameters:**
  * **a** (*array_like* *,* *len* *(**shape* *)*  *>= 1*) – Tensors to “dot”.
  * **b** (*array_like* *,* *len* *(**shape* *)*  *>= 1*) – Tensors to “dot”.
  * **axes** ([*int*](https://docs.python.org/3/library/functions.html#int) *or*  *(**2* *,* *)* *array_like*) – 
    * integer_like
      If an int N, sum over the last N axes of a and the first N axes
      of b in order. The sizes of the corresponding axes must match.
    * (2,) array_like
      Or, a list of axes to be summed over, first sequence applying to a,
      second to b. Both elements array_like must be of the same length.

#### SEE ALSO
[`dot`](maxframe.tensor.dot.md#maxframe.tensor.dot), [`einsum`](maxframe.tensor.einsum.md#maxframe.tensor.einsum)

### Notes

Three common use cases are:

> * `axes = 0` : tensor product $a\otimes b$
> * `axes = 1` : tensor dot product $a\cdot b$
> * `axes = 2` : (default) tensor double contraction $a:b$

When axes is integer_like, the sequence for evaluation will be: first
the -Nth axis in a and 0th axis in b, and the -1th axis in a and
Nth axis in b last.

When there is more than one axis to sum over - and they are not the last
(first) axes of a (b) - the argument axes should consist of
two sequences of the same length, with the first axis to sum over given
first in both sequences, the second axis second, and so forth.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

A “traditional” example:

```pycon
>>> a = mt.arange(60.).reshape(3,4,5)
>>> b = mt.arange(24.).reshape(4,3,2)
>>> c = mt.tensordot(a,b, axes=([1,0],[0,1]))
>>> c.shape
(5, 2)
```

```pycon
>>> r = c.execute()
>>> r
array([[ 4400.,  4730.],
       [ 4532.,  4874.],
       [ 4664.,  5018.],
       [ 4796.,  5162.],
       [ 4928.,  5306.]])
```

```pycon
>>> # A slower but equivalent way of computing the same...
>>> ra = np.arange(60.).reshape(3,4,5)
>>> rb = np.arange(24.).reshape(4,3,2)
>>> d = np.zeros((5,2))
>>> for i in range(5):
...   for j in range(2):
...     for k in range(3):
...       for n in range(4):
...         d[i,j] += ra[k,n,i] * rb[n,k,j]
>>> r == d
array([[ True,  True],
       [ True,  True],
       [ True,  True],
       [ True,  True],
       [ True,  True]], dtype=bool)
```

An extended example taking advantage of the overloading of + and \*:

```pycon
>>> a = mt.array(range(1, 9))
>>> a.shape = (2, 2, 2)
>>> A = mt.array(('a', 'b', 'c', 'd'), dtype=object)
>>> A.shape = (2, 2)
>>> a.execute(); A.execute()
array([[[1, 2],
        [3, 4]],
       [[5, 6],
        [7, 8]]])
array([[a, b],
       [c, d]], dtype=object)
```

```pycon
>>> mt.tensordot(a, A).execute() # third argument default is 2 for double-contraction
array([abbcccdddd, aaaaabbbbbbcccccccdddddddd], dtype=object)
```

```pycon
>>> mt.tensordot(a, A, 1).execute()
array([[[acc, bdd],
        [aaacccc, bbbdddd]],
       [[aaaaacccccc, bbbbbdddddd],
        [aaaaaaacccccccc, bbbbbbbdddddddd]]], dtype=object)
```

```pycon
>>> mt.tensordot(a, A, 0).execute() # tensor product (result too long to incl.)
array([[[[[a, b],
          [c, d]],
          ...
```

```pycon
>>> mt.tensordot(a, A, (0, 1)).execute()
array([[[abbbbb, cddddd],
        [aabbbbbb, ccdddddd]],
       [[aaabbbbbbb, cccddddddd],
        [aaaabbbbbbbb, ccccdddddddd]]], dtype=object)
```

```pycon
>>> mt.tensordot(a, A, (2, 1)).execute()
array([[[abb, cdd],
        [aaabbbb, cccdddd]],
       [[aaaaabbbbbb, cccccdddddd],
        [aaaaaaabbbbbbbb, cccccccdddddddd]]], dtype=object)
```

```pycon
>>> mt.tensordot(a, A, ((0, 1), (0, 1))).execute()
array([abbbcccccddddddd, aabbbbccccccdddddddd], dtype=object)
```

```pycon
>>> mt.tensordot(a, A, ((2, 1), (1, 0))).execute()
array([acccbbdddd, aaaaacccccccbbbbbbdddddddd], dtype=object)
```
