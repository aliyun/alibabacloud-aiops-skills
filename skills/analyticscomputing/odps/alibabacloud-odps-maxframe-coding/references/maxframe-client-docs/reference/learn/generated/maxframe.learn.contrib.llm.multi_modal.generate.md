# maxframe.learn.contrib.llm.multi_modal.generate

### maxframe.learn.contrib.llm.multi_modal.generate(data, model: MultiModalLLM, prompt_template: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], params: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] = None)

Generate text with multi model llm based on given data and prompt template.

* **Parameters:**
  * **data** ([*DataFrame*](../../dataframe/generated/maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *or* [*Series*](../../dataframe/generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Input data used for generation. Can be maxframe DataFrame, Series that contain text to be processed.
  * **model** (*MultiModalLLM*) – Language model instance support **MultiModal** inputs used for text generation.
  * **prompt_template** (*List* *[**Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[**Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]* *]* *]*) – 

    List of message with column names as placeholders. Each message contains a role and content. Content is a list of dict, each dict contains a text or image, the value can reference column data from input.

    Here is an example of prompt template.
    ```python
    [
        {
            "role": "<role>",  # e.g. "user" or "assistant"
            "content": [
                {
                    # At least one of these fields is required
                    "image": "<image_data_url>",  # optional
                    "text": "<prompt_text_template>"  # optional
                },
                ...
            ]
        }
    ]
    ```

    Where:
    - `text` can be a Python format string using column names from input data as parameters (e.g. `"{column_name}"`)
    - `image` should be a DataURL string following [RFC2397](https://en.wikipedia.org/wiki/Data_URI_scheme) standard with format.

    ```none
    data:<mime_type>[;base64],<column_name>
    ```

params
: Additional parameters for generation configuration, by default None.
  Can include settings like temperature, max_tokens, etc.

* **Returns:**
  Generated text raw response and success status. If the success is False, the generated text will return the
  error message.
* **Return type:**
  [DataFrame](../../dataframe/generated/maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Notes

- The `api_key_resource` parameter should reference a text file resource in MaxCompute that contains only your DashScope API key.
- Using DashScope services requires enabling public network access for your MaxCompute project. This can be configured through the MaxCompute console by [enabling the Internet access feature](https://help.aliyun.com/zh/maxcompute/user-guide/network-connection-process) for your project. Without this configuration, the API calls to DashScope will fail due to network connectivity issues.

### Examples

You can initialize a DashScope multi-modal model (such as qwen-vl-max) by providing a model name and an `api_key_resource`.
The `api_key_resource` is a MaxCompute resource name that points to a text file containing a [DashScope](https://dashscope.aliyun.com/) API key.

```pycon
>>> from maxframe.learn.contrib.llm.models.dashscope import DashScopeMultiModalLLM
>>> import maxframe.dataframe as md
>>>
>>> model = DashScopeMultiModalLLM(
...     name="qwen-vl-max",
...     api_key_resource="<api-key-resource-name>"
... )
```

We use Data Url Schema to provide multi modal input in prompt template, here is an example to fill in the image from table.

Assuming you have a MaxCompute table with two columns: `image_id` (as the index) and `encoded_image_data_base64` (containing Base64 encoded image data),
you can construct a prompt message template as follows:

```pycon
>>> df = md.read_odps_table("image_content", index_col="image_id")
```

```pycon
>>> prompt_template = [
...     {
...         "role": "user",
...         "content": [
...             {
...                 "image": "data:image/png;base64,encoded_image_data_base64",
...             },
...             {
...                 "text": "Analyze this image in detail",
...             },
...         ],
...     },
... ]
>>> result = model.generate(df, prompt_template)
>>> result.execute()
```
