# maxframe.tensor.average

### maxframe.tensor.average(a, axis=None, weights=None, returned=False)

Compute the weighted average along the specified axis.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing data to be averaged. If a is not a tensor, a
    conversion is attempted.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which to average a.  The default,
    axis=None, will average over all of the elements of the input tensor.
    If axis is negative it counts from the last to the first axis.

    If axis is a tuple of ints, averaging is performed on all of the axes
    specified in the tuple instead of a single axis or all the axes as
    before.
  * **weights** (*array_like* *,* *optional*) – A tensor of weights associated with the values in a. Each value in
    a contributes to the average according to its associated weight.
    The weights tensor can either be 1-D (in which case its length must be
    the size of a along the given axis) or of the same shape as a.
    If weights=None, then all data in a are assumed to have a
    weight equal to one.
  * **returned** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Default is False. If True, the tuple (average, sum_of_weights)
    is returned, otherwise only the average is returned.
    If weights=None, sum_of_weights is equivalent to the number of
    elements over which the average is taken.
* **Returns:**
  **average, [sum_of_weights]** – Return the average along the specified axis. When returned is True,
  return a tuple with the average as the first element and the sum
  of the weights as the second element. The return type is Float
  if a is of integer type, otherwise it is of the same type as a.
  sum_of_weights is of the same type as average.
* **Return type:**
  tensor_type or double
* **Raises:**
  * [**ZeroDivisionError**](https://docs.python.org/3/library/exceptions.html#ZeroDivisionError) – When all weights along axis are zero. See numpy.ma.average for a
        version robust to this type of error.
  * [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – When the length of 1D weights is not the same as the shape of a
        along axis.

#### SEE ALSO
[`mean`](maxframe.tensor.mean.md#maxframe.tensor.mean)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> data = list(range(1,5))
>>> data
[1, 2, 3, 4]
>>> mt.average(data).execute()
2.5
>>> mt.average(range(1,11), weights=range(10,0,-1)).execute()
4.0
```

```pycon
>>> data = mt.arange(6).reshape((3,2))
>>> data.execute()
array([[0, 1],
       [2, 3],
       [4, 5]])
>>> mt.average(data, axis=1, weights=[1./4, 3./4]).execute()
array([ 0.75,  2.75,  4.75])
>>> mt.average(data, weights=[1./4, 3./4]).execute()
Traceback (most recent call last):
...
TypeError: Axis must be specified when shapes of a and weights differ.
```
