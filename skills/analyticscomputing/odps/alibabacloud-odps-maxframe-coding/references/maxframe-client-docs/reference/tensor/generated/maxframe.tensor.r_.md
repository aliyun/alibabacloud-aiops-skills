# maxframe.tensor.r_

### maxframe.tensor.r_ *= <maxframe.tensor.lib.index_tricks.RClass object>*

Translates slice objects to concatenation along the first axis.

This is a simple way to build up tensor quickly. There are two use cases.

1. If the index expression contains comma separated tensors, then stack
   them along their first axis.
2. If the index expression contains slice notation or scalars then create
   a 1-D tensor with a range indicated by the slice notation.

If slice notation is used, the syntax `start:stop:step` is equivalent
to `mt.arange(start, stop, step)` inside of the brackets. However, if
`step` is an imaginary number (i.e. 100j) then its integer portion is
interpreted as a number-of-points desired and the start and stop are
inclusive. In other words `start:stop:stepj` is interpreted as
`mt.linspace(start, stop, step, endpoint=1)` inside of the brackets.
After expansion of slice notation, all comma separated sequences are
concatenated together.

Optional character strings placed as the first element of the index
expression can be used to change the output. The strings ‘r’ or ‘c’ result
in matrix output. If the result is 1-D and ‘r’ is specified a 1 x N (row)
matrix is produced. If the result is 1-D and ‘c’ is specified, then a N x 1
(column) matrix is produced. If the result is 2-D then both provide the
same matrix result.

A string integer specifies which axis to stack multiple comma separated
tensors along. A string of two comma-separated integers allows indication
of the minimum number of dimensions to force each entry into as the
second integer (the axis to concatenate along is still the first integer).

A string with three comma-separated integers allows specification of the
axis to concatenate along, the minimum number of dimensions to force the
entries to, and which axis should contain the start of the tensors which
are less than the specified number of dimensions. In other words the third
integer allows you to specify where the 1’s should be placed in the shape
of the tensors that have their shapes upgraded. By default, they are placed
in the front of the shape tuple. The third argument allows you to specify
where the start of the tensor should be instead. Thus, a third argument of
‘0’ would place the 1’s at the end of the tensor shape. Negative integers
specify where in the new shape tuple the last dimension of upgraded tensors
should be placed, so the default is ‘-1’.

* **Parameters:**
  * **function** (*Not a*)
  * **parameters** (*so takes no*)
* **Return type:**
  A concatenated tensor or matrix.

#### SEE ALSO
[`concatenate`](maxframe.tensor.concatenate.md#maxframe.tensor.concatenate)
: Join a sequence of tensors along an existing axis.

[`c_`](maxframe.tensor.c_.md#maxframe.tensor.c_)
: Translates slice objects to concatenation along the second axis.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.r_[mt.array([1,2,3]), 0, 0, mt.array([4,5,6])].execute()
array([1, 2, 3, ..., 4, 5, 6])
>>> mt.r_[-1:1:6j, [0]*3, 5, 6].execute()
array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])
```

String integers specify the axis to concatenate along or the minimum
number of dimensions to force entries into.

```pycon
>>> a = mt.array([[0, 1, 2], [3, 4, 5]])
>>> mt.r_['-1', a, a].execute() # concatenate along last axis
array([[0, 1, 2, 0, 1, 2],
       [3, 4, 5, 3, 4, 5]])
>>> mt.r_['0,2', [1,2,3], [4,5,6]].execute() # concatenate along first axis, dim>=2
array([[1, 2, 3],
       [4, 5, 6]])
```

```pycon
>>> mt.r_['0,2,0', [1,2,3], [4,5,6]].execute()
array([[1],
       [2],
       [3],
       [4],
       [5],
       [6]])
>>> mt.r_['1,2,0', [1,2,3], [4,5,6]].execute()
array([[1, 4],
       [2, 5],
       [3, 6]])
```
