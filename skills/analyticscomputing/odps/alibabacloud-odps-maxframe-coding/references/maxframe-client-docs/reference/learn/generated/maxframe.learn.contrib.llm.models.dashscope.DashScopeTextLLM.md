# maxframe.learn.contrib.llm.models.dashscope.DashScopeTextLLM

### *class* maxframe.learn.contrib.llm.models.dashscope.DashScopeTextLLM(name: [str](https://docs.python.org/3/library/stdtypes.html#str), api_key_resource: [str](https://docs.python.org/3/library/stdtypes.html#str))

DashScope text LLM.

#### \_\_init_\_(name: [str](https://docs.python.org/3/library/stdtypes.html#str), api_key_resource: [str](https://docs.python.org/3/library/stdtypes.html#str))

Initialize a DashScope text LLM.

* **Parameters:**
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The LLM name to use, check DashScope for [available models](https://help.aliyun.com/zh/model-studio/getting-started/models).
  * **api_key_resource** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The MaxCompute resource file name containing the DashScope API key.

### Methods

| [`__init__`](#maxframe.learn.contrib.llm.models.dashscope.DashScopeTextLLM.__init__)(name, api_key_resource)   | Initialize a DashScope text LLM.   |
|----------------------------------------------------------------------------------------------------------------|------------------------------------|
| `classify`(series, labels[, description, ...])                                                                 |                                    |
| `copy`()                                                                                                       |                                    |
| `copy_to`(target)                                                                                              |                                    |
| `extract`(series, schema[, description, ...])                                                                  |                                    |
| `generate`(data, prompt_template[, params])                                                                    |                                    |
| `summarize`(series[, index])                                                                                   |                                    |
| `translate`(series, target_language[, ...])                                                                    |                                    |
| `validate_params`(params)                                                                                      |                                    |

### Attributes

| `api_key_resource`   |    |
|----------------------|----|
| `name`               |    |
