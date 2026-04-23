# maxframe.learn.contrib.llm.deploy.config.ModelDeploymentConfig

### *class* maxframe.learn.contrib.llm.deploy.config.ModelDeploymentConfig(\*args, \*\*kwargs)

Model deployment configuration for extending MaxFrame with custom models.

This configuration is designed for users who need to deploy models that are not
available within MaxFrame’s built-in model offerings. It provides a way to specify
custom deployment solutions by informing each MaxFrame worker which framework to use,
which model path to load, and how to load it.

The configuration assumes that models are already set up in the container image or
mounted paths, and uses the current deploy_config to load them. Users are responsible
for ensuring the runtime environment state and compatibility.

* **Parameters:**
  * **model_name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The name of the model.
  * **model_file** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – 

    The **local** file path of the model, e.g., `"/mnt/models/qwen/"`.
    When using OSS models, this should match one of the `mount_path` values
    in `fs_mounts`.

    Note: OSS paths (`oss://...`) are NOT supported directly. Use `fs_mounts`
    to mount OSS paths to local paths first.
  * **inference_framework_type** ([*InferenceFrameworkEnum*](maxframe.learn.contrib.llm.deploy.framework.InferenceFrameworkEnum.md#maxframe.learn.contrib.llm.deploy.framework.InferenceFrameworkEnum)) – The inference framework of the model.
  * **required_resource_files** (*List* *[**Union* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *Any* *]* *]*) – The required resource files of the model.
  * **load_params** (*Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *Any* *]*) – The load params of the model.
  * **required_cpu** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The required cpu of the model.
  * **required_memory** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The required memory of the model.
  * **required_gu** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The required gu of the model.
  * **required_gpu_memory** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The required gpu memory of the model.
  * **device** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The device of the model. One of “cpu” or “cuda”.
  * **properties** (*Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *Any* *]*) – The properties of the model.
  * **tags** (*List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – The tags of the model.
  * **fs_mounts** (*List* *[**FsMountOptions* *]*) – 

    File system mount configurations for mounting OSS models to local paths.
    Each FsMountOptions contains:
    - `path`: OSS source path, e.g., `"oss://bucket/models/qwen/"`
    - `mount_path`: Local mount path, e.g., `"/mnt/qwen"`
    - `storage_options`: Authentication config (role_arn or AK/SK)

    This is consistent with the `with_fs_mount` decorator pattern.
    The `model_file` should reference the `mount_path` from one of the mounts.
  * **envs** (*Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – Custom environment variables for the inference subprocess.
    Example: `{"CUDA_VISIBLE_DEVICES": "0", "HF_HOME": "/mnt/cache"}`

### Notes

- Preview version for model deployments, all fields could be changed in the future.

**User Responsibility Notice**: Users must have a complete understanding of what
they are computing and ensure they fully comprehend the implications of their
configuration choices. You are responsible for:

* Ensuring model compatibility with the specified inference framework
* Verifying that model files exist and are accessible in the runtime environment
* Confirming that resource requirements (CPU, memory, GPU) are adequate
* Validating that all dependencies and libraries are properly installed
* Understanding the computational behavior and characteristics of your chosen model

#### \_\_init_\_(\*args, \*\*kwargs)

### Methods

| [`__init__`](#maxframe.learn.contrib.llm.deploy.config.ModelDeploymentConfig.__init__)(\*args, \*\*kwargs)   |                                                             |
|--------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| `check_validity`()                                                                                           | Validate the configuration and raise ValueError if invalid. |
| `copy`()                                                                                                     |                                                             |
| `copy_to`(target)                                                                                            |                                                             |
| `is_reasoning_model`()                                                                                       |                                                             |

### Attributes

| `required_memory`          |    |
|----------------------------|----|
| `required_resource_files`  |    |
| `model_file`               |    |
| `device`                   |    |
| `properties`               |    |
| `fs_mounts`                |    |
| `model_name`               |    |
| `load_params`              |    |
| `envs`                     |    |
| `required_cpu`             |    |
| `required_gpu_memory`      |    |
| `tags`                     |    |
| `required_gu`              |    |
| `inference_framework_type` |    |
