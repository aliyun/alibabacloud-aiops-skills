# maxframe.learn.contrib.llm.models.dashscope.DashScopeMultiModalLLM

### *class* maxframe.learn.contrib.llm.models.dashscope.DashScopeMultiModalLLM(name: [str](https://docs.python.org/3/library/stdtypes.html#str), api_key_resource: [str](https://docs.python.org/3/library/stdtypes.html#str))

DashScope multi-modal LLM.

#### \_\_init_\_(name: [str](https://docs.python.org/3/library/stdtypes.html#str), api_key_resource: [str](https://docs.python.org/3/library/stdtypes.html#str))

Initialize a DashScope multi-modal LLM.

* **Parameters:**
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The LLM name to use, check DashScope for [available models](https://help.aliyun.com/zh/model-studio/getting-started/models).
  * **api_key_resource** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The MaxCompute resource file name containing the DashScope API key.

### Methods

| [`__init__`](#maxframe.learn.contrib.llm.models.dashscope.DashScopeMultiModalLLM.__init__)(name, api_key_resource)   | Initialize a DashScope multi-modal LLM.   |
|----------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| `copy`()                                                                                                             |                                           |
| `copy_to`(target)                                                                                                    |                                           |
| `generate`(data, prompt_template[, params])                                                                          |                                           |
| `validate_params`(params)                                                                                            |                                           |

### Attributes

| `api_key_resource`   |    |
|----------------------|----|
| `name`               |    |
