# maxframe.dataframe.DataFrame.mf.rebalance

#### DataFrame.mf.rebalance(axis=0, factor=None, num_partitions=None)

Make data more balanced across entire cluster.

* **Parameters:**
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The axis to rebalance.
  * **factor** ([*float*](https://docs.python.org/3/library/functions.html#float)) – Specified so that number of chunks after balance is
    total number of input chunks \* factor.
  * **num_partitions** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Specified so the number of chunks are at most
    num_partitions.
* **Returns:**
  Result of DataFrame or Series after rebalanced.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
