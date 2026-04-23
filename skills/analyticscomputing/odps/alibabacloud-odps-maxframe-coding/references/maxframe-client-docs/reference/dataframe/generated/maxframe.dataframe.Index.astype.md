# maxframe.dataframe.Index.astype

#### Index.astype(dtype, copy=True)

Create an Index with values cast to dtypes.

The class of a new Index is determined by dtype. When conversion is
impossible, a ValueError exception is raised.

* **Parameters:**
  * **dtype** (*numpy dtype* *or* *pandas type*) – Note that any signed integer dtype is treated as `'int64'`,
    and any unsigned integer dtype is treated as `'uint64'`,
    regardless of the size.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – By default, astype always returns a newly allocated object.
    If copy is set to False and internal requirements on dtype are
    satisfied, the original data is used to create a new Index
    or the original Index is returned.
* **Returns:**
  Index with values cast to specified dtype.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)
