# maxframe.learn.contrib.llm.text.summary

### maxframe.learn.contrib.llm.text.summary(series, model: TextGenLLM, index=None)

Generate summaries for text content in a series using a language model.

* **Parameters:**
  * **series** ([*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – A maxframe Series containing text data to be summarized.
    Each element should be a text string.
  * **model** (*TextGenLLM*) – Language model instance used for text summarization.
  * **index** (*array-like* *,* *optional*) – Index for the output series, by default None, will generate new index.
* **Returns:**
  A DataFrame containing the generated summaries and success status.
  Columns include ‘summary’ (generated summary text) and ‘success’ (boolean status).
  If ‘success’ is False, the ‘summary’ column will contain error information instead of the expected output.
* **Return type:**
  [DataFrame](../../dataframe/generated/maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> from maxframe.learn.contrib.llm.models.managed import ManagedTextGenLLM
>>> import maxframe.dataframe as md
>>>
>>> # Initialize the model
>>> llm = ManagedTextGenLLM(name="Qwen3-0.6B")
>>>
>>> # Create sample data
>>> texts = md.Series([
...     "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
...     "Deep learning uses neural networks with multiple layers to model and understand complex patterns in data."
... ])
>>>
>>> # Generate summaries
>>> result = summary(texts, llm)
>>> result.execute()
```

### Notes

**Preview:** This API is in preview state and may be unstable.
The interface may change in future releases.
