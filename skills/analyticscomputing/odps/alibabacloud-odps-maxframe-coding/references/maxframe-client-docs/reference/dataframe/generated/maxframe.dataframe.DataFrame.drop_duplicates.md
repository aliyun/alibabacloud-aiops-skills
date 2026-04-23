# maxframe.dataframe.DataFrame.drop_duplicates

#### DataFrame.drop_duplicates(subset=None, keep='first', inplace=False, ignore_index=False, method='auto', default_index_type=None)

Return DataFrame with duplicate rows removed.

Considering certain columns is optional. Indexes, including time indexes
are ignored.

* **Parameters:**
  * **subset** (*column label* *or* *sequence* *of* *labels* *,* *optional*) – Only consider certain columns for identifying duplicates, by
    default use all of the columns.
  * **keep** ( *{'first'* *,*  *'last'* *,* *False}* *,* *default 'first'*) – Determines which duplicates (if any) to keep.
    - `first` : Drop duplicates except for the first occurrence.
    - `last` : Drop duplicates except for the last occurrence.
    - `any` : Drop duplicates except for a random occurrence.
    - False : Drop all duplicates.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to drop duplicates in place or to return a copy.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
* **Returns:**
  DataFrame with duplicates removed or None if `inplace=True`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
