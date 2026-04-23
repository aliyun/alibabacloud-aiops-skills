# Executing and getting results

## Lazy execution

MaxFrame uses lazy execution to make use of global optimization. That is, unless
execution results are needed at client side locally, MaxFrame expressions are not
executed without manual execution. For instance,

```python
>>> df.head(3)
DataFrame <op=DataFrameILoc, key=182b756be8a9f15c937a04223f11ffba>
```

is not executed, while

```python
>>> df.head(3).execute()
          0         1         2
0  0.167771  0.568741  0.877450
1  0.037518  0.796745  0.072169
2  0.052900  0.936048  0.307194
```

will trigger execution. Here we list several conditions that will trigger
execution below.

* Direct `execute()` calls.
* [`maxframe.dataframe.DataFrame.to_pandas()`](../../reference/dataframe/generated/maxframe.dataframe.DataFrame.to_pandas.md#maxframe.dataframe.DataFrame.to_pandas) calls.
* All plot functions for DataFrame and Series, including [`maxframe.dataframe.DataFrame.plot()`](../../reference/dataframe/generated/maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot),
  [`maxframe.dataframe.DataFrame.plot.bar()`](../../reference/dataframe/generated/maxframe.dataframe.DataFrame.plot.bar.md#maxframe.dataframe.DataFrame.plot.bar) and so on.

## Asynchrous execution

Specifying `wait=False` can make execuiton asynchronous. A [Future object](https://docs.python.org/3/library/concurrent.futures.html#future-objects) will be returned.

```python
>>> fut = df.head(3).execute(wait=False)
>>> fut.wait()
>>> fut.result()
          0         1         2
0  0.167771  0.568741  0.877450
1  0.037518  0.796745  0.072169
2  0.052900  0.936048  0.307194
```

## Obtaining results

You can use `fetch()` function to fetch execution result from executed objects. The fetched
data is a local Python object (i.e., pandas objects or numpy arrays) that can be handled by
local Python libraries.

```python
>>> df.execute().fetch()
          0         1         2
0  0.167771  0.568741  0.877450
1  0.037518  0.796745  0.072169
2  0.052900  0.936048  0.307194
```

Note that `fetch()` will fetch all data behind the MaxFrame object. If you just need to preview
several data, just use `repr()` function or simply call `execute()` method in an interactive
Python environment like IPython or JupyterLab. MaxFrame will simply peek first and last rows.

```python
>>> repr(df.execute())  # or simply df.execute() if in an interactive environment
           0         1         2
0   0.167771  0.568741  0.877450
1   0.037518  0.796745  0.072169
2   0.052900  0.936048  0.307194
...
97  0.167771  0.568741  0.877450
98  0.037518  0.796745  0.072169
99  0.052900  0.936048  0.307194
```
