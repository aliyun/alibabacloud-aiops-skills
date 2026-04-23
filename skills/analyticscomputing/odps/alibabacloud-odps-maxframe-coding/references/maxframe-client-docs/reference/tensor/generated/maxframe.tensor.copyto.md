# maxframe.tensor.copyto

### maxframe.tensor.copyto(dst, src, casting='same_kind', where=True)

Copies values from one array to another, broadcasting as necessary.

Raises a TypeError if the casting rule is violated, and if
where is provided, it selects which elements to copy.

* **Parameters:**
  * **dst** (*Tensor*) – The tensor into which values are copied.
  * **src** (*array_like*) – The tensor from which values are copied.
  * **casting** ( *{'no'* *,*  *'equiv'* *,*  *'safe'* *,*  *'same_kind'* *,*  *'unsafe'}* *,* *optional*) – 

    Controls what kind of data casting may occur when copying.
    > * ’no’ means the data types should not be cast at all.
    > * ’equiv’ means only byte-order changes are allowed.
    > * ’safe’ means only casts which can preserve values are allowed.
    > * ’same_kind’ means only safe casts or casts within a kind,
    >   like float64 to float32, are allowed.
    > * ’unsafe’ means any data conversions may be done.
  * **where** (*array_like* *of* [*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – A boolean tensor which is broadcasted to match the dimensions
    of dst, and selects elements to copy from src to dst
    wherever it contains the value True.
