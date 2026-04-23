# maxframe.tensor.fix

### maxframe.tensor.fix(x, out=None, \*\*kwargs)

Round to nearest integer towards zero.

Round a tensor of floats element-wise to nearest integer towards zero.
The rounded values are returned as floats.

* **Parameters:**
  * **x** (*array_like*) – An tensor of floats to be rounded
  * **out** (*Tensor* *,* *optional*) – Output tensor
* **Returns:**
  **out** – The array of rounded numbers
* **Return type:**
  Tensor of floats

#### SEE ALSO
[`trunc`](maxframe.tensor.trunc.md#maxframe.tensor.trunc), [`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor), [`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil)

[`around`](maxframe.tensor.around.md#maxframe.tensor.around)
: Round to given number of decimals

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.fix(3.14).execute()
3.0
>>> mt.fix(3).execute()
3.0
>>> mt.fix([2.1, 2.9, -2.1, -2.9]).execute()
array([ 2.,  2., -2., -2.])
```
