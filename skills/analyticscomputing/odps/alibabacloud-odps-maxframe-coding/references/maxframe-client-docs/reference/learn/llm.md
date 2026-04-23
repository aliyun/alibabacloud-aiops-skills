<a id="learn-llm-ref"></a>

# LLM Integration

## LLM Models

| [`dashscope.DashScopeMultiModalLLM`](generated/maxframe.learn.contrib.llm.models.dashscope.DashScopeMultiModalLLM.md#maxframe.learn.contrib.llm.models.dashscope.DashScopeMultiModalLLM)(name, ...)   | DashScope multi-modal LLM.   |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| [`dashscope.DashScopeTextLLM`](generated/maxframe.learn.contrib.llm.models.dashscope.DashScopeTextLLM.md#maxframe.learn.contrib.llm.models.dashscope.DashScopeTextLLM)(name, ...)                     | DashScope text LLM.          |
| [`managed.ManagedTextLLM`](generated/maxframe.learn.contrib.llm.models.managed.ManagedTextLLM.md#maxframe.learn.contrib.llm.models.managed.ManagedTextLLM)                                            | alias of `ManagedTextGenLLM` |

## Custom Model Configuration

| [`config.ModelDeploymentConfig`](generated/maxframe.learn.contrib.llm.deploy.config.ModelDeploymentConfig.md#maxframe.learn.contrib.llm.deploy.config.ModelDeploymentConfig)(\*args, \*\*kwargs)   | Model deployment configuration for extending MaxFrame with custom models.   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|

<a id="module-0"></a>

| [`framework.InferenceFrameworkEnum`](generated/maxframe.learn.contrib.llm.deploy.framework.InferenceFrameworkEnum.md#maxframe.learn.contrib.llm.deploy.framework.InferenceFrameworkEnum)(value)   |    |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----|

## Text Generate Functions

| [`multi_modal.generate`](generated/maxframe.learn.contrib.llm.multi_modal.generate.md#maxframe.learn.contrib.llm.multi_modal.generate)(data, model, ...[, params])   | Generate text with multi model llm based on given data and prompt template.                        |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| [`text.extract`](generated/maxframe.learn.contrib.llm.text.extract.md#maxframe.learn.contrib.llm.text.extract)(series, model, schema[, ...])                         | Extract structured information from text content in a series using a language model.               |
| [`text.generate`](generated/maxframe.learn.contrib.llm.text.generate.md#maxframe.learn.contrib.llm.text.generate)(data, model, prompt_template)                      | Generate text using a text language model based on given data and prompt template.                 |
| [`text.translate`](generated/maxframe.learn.contrib.llm.text.translate.md#maxframe.learn.contrib.llm.text.translate)(series, model, ...[, index])                    | Translate text content in a series using a language model from source language to target language. |
