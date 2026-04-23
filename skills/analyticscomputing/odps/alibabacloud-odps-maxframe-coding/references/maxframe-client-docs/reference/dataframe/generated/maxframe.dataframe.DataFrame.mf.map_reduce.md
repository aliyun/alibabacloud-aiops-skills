# maxframe.dataframe.DataFrame.mf.map_reduce

#### DataFrame.mf.map_reduce(mapper: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable) | [None](https://docs.python.org/3/library/constants.html#None) = None, reducer: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable) | [None](https://docs.python.org/3/library/constants.html#None) = None, group_cols: [List](https://docs.python.org/3/library/typing.html#typing.List)[[Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = None, , order_cols: [List](https://docs.python.org/3/library/typing.html#typing.List)[[Any](https://docs.python.org/3/library/typing.html#typing.Any)] = None, ascending: [bool](https://docs.python.org/3/library/functions.html#bool) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[bool](https://docs.python.org/3/library/functions.html#bool)] = True, combiner: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable) = None, batch_rows: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = 1024, mapper_dtypes: Series = None, mapper_index: Index = None, mapper_batch_rows: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, reducer_dtypes: Series = None, reducer_index: Index = None, reducer_batch_rows: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, ignore_index: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Map-reduce API over certain DataFrames. This function is roughly
a shortcut for

```python
df.mf.apply_chunk(mapper).groupby(group_keys).mf.apply_chunk(reducer)
```

* **Parameters:**
  * **mapper** (*function* *or* [*type*](https://docs.python.org/3/library/functions.html#type)) – Mapper function or class.
  * **reducer** (*function* *or* [*type*](https://docs.python.org/3/library/functions.html#type)) – Reducer function or class.
  * **group_cols** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – The keys to group after mapper. If absent, all columns in the mapped
    DataFrame will be used.
  * **order_cols** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – The columns to sort after groupby.
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *[*[*bool*](https://docs.python.org/3/library/functions.html#bool) *] or* *None*) – Whether columns should be in ascending order or not, only effective when
    order_cols are specified. If a list of booleans are passed, orders of
    every column in order_cols are specified.
  * **combiner** (*function* *or* *class*) – Combiner function or class. Should accept and returns the same schema
    of mapper outputs.
  * **batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None*) – Rows in batches for mappers and reducers. Ignored if mapper_batch_rows
    specified for mappers or reducer_batch_rows specified for reducers.
    1024 by default.
  * **mapper_dtypes** (*pd.Series* *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *or* *None*) – Output dtypes of mapper stage.
  * **mapper_index** (*pd.Index* *or* *None*) – Index of DataFrame returned by mappers.
  * **mapper_batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None*) – Rows in batches for mappers. If specified, batch_rows will be ignored
    for mappers.
  * **reducer_dtypes** (*pd.Series* *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *or* *None*) – Output dtypes of reducer stage.
  * **reducer_index** (*pd.Index* *or* *None*) – Index of DataFrame returned by reducers.
  * **reducer_batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None*) – Rows in batches for mappers. If specified, batch_rows will be ignored
    for reducers.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If true, indexes generated at mapper or reducer functions will be ignored.
* **Returns:**
  **output** – Result DataFrame after map and reduce.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

We first define a DataFrame with a column of several words.

```pycon
>>> from collections import defaultdict
>>> import maxframe.dataframe as md
>>> from maxframe.udf import with_running_options
>>> df = pd.DataFrame(
>>>     {
>>>         "name": ["name key", "name", "key", "name", "key name"],
>>>         "id": [4, 2, 4, 3, 3],
>>>         "fid": [5.3, 3.5, 4.2, 2.2, 4.1],
>>>     }
>>> )
```

Then we write a mapper function which accepts batches in the DataFrame
and returns counts of words in every row.

```pycon
>>> def mapper(batch):
>>>     word_to_count = defaultdict(lambda: 0)
>>>     for words in batch["name"]:
>>>         for w in words.split():
>>>             word_to_count[w] += 1
>>>     return pd.DataFrame(
>>>         [list(tp) for tp in word_to_count.items()], columns=["word", "count"]
>>>     )
```

After that we write a reducer function which aggregates records with
the same word. Running options such as CPU specifications can be supplied
as well.

```pycon
>>> @with_running_options(cpu=2)
>>> class TestReducer:
>>>     def __init__(self):
>>>         self._word_to_count = defaultdict(lambda: 0)
>>>
>>>     def __call__(self, batch, end=False):
>>>         word = None
>>>         for _, row in batch.iterrows():
>>>             word = row.iloc[0]
>>>             self._word_to_count[row.iloc[0]] += row.iloc[1]
>>>         if end:
>>>             return pd.DataFrame(
>>>                 [[word, self._word_to_count[word]]], columns=["word", "count"]
>>>             )
>>>
>>>     def close(self):
>>>         # you can do several cleanups here
>>>         print("close")
```

Finally we can call map_reduce with mappers and reducers specified above.

```pycon
>>> res = df.mf.map_reduce(
>>>     mapper,
>>>     TestReducer,
>>>     group_cols=["word"],
>>>     mapper_dtypes={"word": "str", "count": "int"},
>>>     mapper_index=pd.Index([0]),
>>>     reducer_dtypes={"word": "str", "count": "int"},
>>>     reducer_index=pd.Index([0]),
>>>     ignore_index=True,
>>> )
>>> res.execute().fetch()
   word  count
0   key      3
1  name      4
```

#### SEE ALSO
[`DataFrame.mf.apply_chunk`](maxframe.dataframe.DataFrame.mf.apply_chunk.md#maxframe.dataframe.DataFrame.mf.apply_chunk), `DataFrame.groupby.mf.apply_chunk`
