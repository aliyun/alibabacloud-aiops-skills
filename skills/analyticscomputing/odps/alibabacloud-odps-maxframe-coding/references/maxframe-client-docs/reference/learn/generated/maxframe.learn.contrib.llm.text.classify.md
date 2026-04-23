# maxframe.learn.contrib.llm.text.classify

### maxframe.learn.contrib.llm.text.classify(series, model: TextGenLLM, labels: [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)], description: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, examples: [List](https://docs.python.org/3/library/typing.html#typing.List)[[Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]] = None, index=None)

Classify text content in a series with given labels using a language model.

* **Parameters:**
  * **series** ([*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – A maxframe Series containing text data to be classified.
    Each element should be a text string.
  * **model** (*TextGenLLM*) – Language model instance used for text classification.
  * **labels** (*List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – List of labels to classify the text into.
  * **description** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Description of the classification task to help the model understand the context.
  * **examples** (*List* *[**Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]* *,* *optional*) – Examples of the classification task, like [{“text”: “text…”, “label”: “A”, “reason”: “reason…”}],
    to help LLM better understand your classification rules.
  * **index** (*array-like* *,* *optional*) – Index for the output series, by default None, will generate new index.
* **Returns:**
  A DataFrame containing the generated classification results and success status.
  Columns include ‘label’ (predicted label), ‘reason’ (reasoning), and ‘success’ (boolean status).
  If ‘success’ is False, the ‘label’ and ‘reason’ columns will contain error information instead of the expected output.
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
...     "I love this product! It's amazing!",
...     "This is terrible, worst purchase ever.",
...     "It's okay, nothing special."
... ])
>>>
>>> # Classify sentiment
>>> labels = ["positive", "negative", "neutral"]
>>> description = "Classify the sentiment of customer reviews"
>>> examples = [
...     {"text": "Great product!", "label": "positive", "reason": "Expresses satisfaction"},
...     {"text": "Poor quality", "label": "negative", "reason": "Expresses dissatisfaction"}
... ]
>>> result = classify(texts, llm, labels=labels, description=description, examples=examples)
>>> result.execute()
```

### Notes

**Preview:** This API is in preview state and may be unstable.
The interface may change in future releases.
