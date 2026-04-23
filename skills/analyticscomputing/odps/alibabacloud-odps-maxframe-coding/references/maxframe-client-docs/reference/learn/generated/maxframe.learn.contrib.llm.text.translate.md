# maxframe.learn.contrib.llm.text.translate

### maxframe.learn.contrib.llm.text.translate(series, model: TextGenLLM, source_language: [str](https://docs.python.org/3/library/stdtypes.html#str), target_language: [str](https://docs.python.org/3/library/stdtypes.html#str), index=None)

Translate text content in a series using a language model from source language to target language.

* **Parameters:**
  * **series** ([*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – A maxframe Series containing text data to translate.
    Each element should be a text string.
  * **model** (*TextGenLLM*) – Language model instance used for text translation.
  * **source_language** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Source language of the text (e.g., ‘en’, ‘zh’, ‘ja’).
  * **target_language** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Target language for translation (e.g., ‘en’, ‘zh’, ‘ja’).
  * **index** (*array-like* *,* *optional*) – Index for the output series, by default None, will generate new index.
* **Returns:**
  A DataFrame containing the generated translations and success status.
  Columns include ‘output’ (translated text) and ‘success’ (boolean status).
  If ‘success’ is False, the ‘output’ column will contain error information instead of the expected output.
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
...     "Hello, how are you?",
...     "Machine learning is fascinating."
... ])
>>>
>>> # Translate from English to Chinese
>>> result = translate(texts, llm, source_language="en", target_language="zh")
>>> result.execute()
```

### Notes

**Preview:** This API is in preview state and may be unstable.
The interface may change in future releases.
