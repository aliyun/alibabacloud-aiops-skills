# maxframe.learn.contrib.llm.text.generate

### maxframe.learn.contrib.llm.text.generate(data, model: TextGenLLM, prompt_template: [List](https://docs.python.org/3/library/typing.html#typing.List)[[Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]], params: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] = None)

Generate text using a text language model based on given data and prompt template.

* **Parameters:**
  * **data** ([*DataFrame*](../../dataframe/generated/maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *or* [*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Input data used for generation. Can be maxframe DataFrame, Series that contain text to be processed.
  * **model** (*TextLLM*) – Language model instance used for text generation.
  * **prompt_template** (*List* *[**Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – 

    Dictionary containing the conversation messages template. Use `{col_name}` as a placeholder to reference
    column data from input data.

    Usually in format of [{“role”: “user”, “content”: “{query}”}], same with openai api schema.
  * **params** (*Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *Any* *]* *,* *optional*) – Additional parameters for generation configuration, by default None.
    Can include settings like temperature, max_tokens, etc.
* **Returns:**
  Generated text raw response and success status. If the success is False, the generated text will return the
  error message.
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
>>> # Prepare prompt template
>>> messages = [
...     {
...         "role": "user",
...         "content": "Help answer following question: {query}",
...     },
... ]
```

```pycon
>>> # Create sample data
>>> df = md.DataFrame({"query": ["What is machine learning?"]})
>>>
>>> # Generate response
>>> result = generate(df, llm, prompt_template=messages)
>>> result.execute()
```
