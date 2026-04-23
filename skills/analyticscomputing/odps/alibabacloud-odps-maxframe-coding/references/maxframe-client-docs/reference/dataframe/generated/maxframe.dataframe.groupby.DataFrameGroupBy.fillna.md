# maxframe.dataframe.groupby.DataFrameGroupBy.fillna

#### DataFrameGroupBy.fillna(value=None, method=None, axis=None, limit=None, downcast=None)

Fill NA/NaN values using the specified method

value:  scalar, dict, Series, or DataFrame
: Value to use to fill holes (e.g. 0), alternately a dict/Series/DataFrame
  of values specifying which value to use for each index (for a Series) or
  column (for a DataFrame). Values not in the dict/Series/DataFrame
  will not be filled. This value cannot be a list.

method: {‘backfill’,’bfill’,’ffill’,None}, default None
axis:   {0 or ‘index’, 1 or ‘column’}
limit:  int, default None

> If method is specified, this is the maximum number of consecutive
> NaN values to forward/backward fill

downcast:   dict, default None
: A dict of item->dtype of what to downcast if possible,
  or the string ‘infer’ which will try to downcast to an appropriate equal type

return: DataFrame or None
