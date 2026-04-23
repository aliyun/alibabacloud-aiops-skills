# maxframe.learn.contrib.llm.text.extract

### maxframe.learn.contrib.llm.text.extract(series, model: TextGenLLM, schema: [Any](https://docs.python.org/3/library/typing.html#typing.Any), description: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, examples: [List](https://docs.python.org/3/library/typing.html#typing.List)[[Tuple](https://docs.python.org/3/library/typing.html#typing.Tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]] = None, index=None)

Extract structured information from text content in a series using a language model.

* **Parameters:**
  * **series** ([*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – A maxframe Series containing text data to extract information from.
    Each element should be a text string.
  * **model** (*TextGenLLM*) – Language model instance used for information extraction.
  * **schema** (*Any*) – Schema definition for the extraction. Can be a dictionary defining the structure
    or a Pydantic BaseModel class that will be converted to JSON schema.
  * **description** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Description of the extraction task to help the model understand what to extract.
  * **examples** (*List* *[**Tuple* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]* *,* *optional*) – Examples of the extraction task in format [(input_text, expected_output), …],
    to help LLM better understand the extraction requirements.
  * **index** (*array-like* *,* *optional*) – Index for the output series, by default None, will generate new index.
* **Returns:**
  A DataFrame containing the extracted information and success status.
  Columns include ‘output’ (extracted structured data) and ‘success’ (boolean status).
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
...     "John Smith, age 30, works as a Software Engineer at Google.",
...     "Alice Johnson, 25 years old, is a Data Scientist at Microsoft."
... ])
>>>
>>> # Define extraction schema
>>> schema = {
...     "name": "string",
...     "age": "integer",
...     "job_title": "string",
...     "company": "string"
... }
>>>
>>> # Extract structured information
>>> description = "Extract person information from text"
>>> examples = [
...     ("Bob Brown, 35, Manager at Apple", '{"name": "Bob Brown", "age": 35, "job_title": "Manager", "company": "Apple"}')
... ]
>>> result = extract(texts, llm, schema=schema, description=description, examples=examples)
>>> result.execute()
```

### Notes

**Preview:** This API is in preview state and may be unstable.
The interface may change in future releases.
