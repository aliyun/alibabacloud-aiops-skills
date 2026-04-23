# maxframe.dataframe.read_pandas

### maxframe.dataframe.read_pandas(data: DataFrame | Series | Index, \*\*kwargs) → [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) | [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) | [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

Create MaxFrame objects from pandas.

* **Parameters:**
  * **data** (*Union* *[**pd.DataFrame* *,* *pd.Series* *,* *pd.Index* *]*) – pandas data
  * **kwargs** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – arguments to be passed to initializers.
* **Returns:**
  **result** – result MaxFrame object
* **Return type:**
  Union[[DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame), [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series), [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)]
