# maxframe.learn.contrib.xgboost.callback.EarlyStopping

### *class* maxframe.learn.contrib.xgboost.callback.EarlyStopping(, rounds: [int](https://docs.python.org/3/library/functions.html#int), metric_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, data_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, maximize: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = None, save_best: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = False, min_delta: [float](https://docs.python.org/3/library/functions.html#float) = 0.0, \*\*kw)

#### \_\_init_\_(, rounds: [int](https://docs.python.org/3/library/functions.html#int), metric_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, data_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, maximize: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = None, save_best: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = False, min_delta: [float](https://docs.python.org/3/library/functions.html#float) = 0.0, \*\*kw) → [None](https://docs.python.org/3/library/constants.html#None)

### Methods

| [`__init__`](#maxframe.learn.contrib.xgboost.callback.EarlyStopping.__init__)(\*, rounds[, metric_name, ...])   |    |
|-----------------------------------------------------------------------------------------------------------------|----|
| `copy`()                                                                                                        |    |
| `copy_to`(target)                                                                                               |    |
| `from_local`(callback_obj)                                                                                      |    |
| `has_custom_code`()                                                                                             |    |
| `remote_to_local`(remote_obj)                                                                                   |    |
| `to_local`()                                                                                                    |    |

### Attributes

| `rounds`      |    |
|---------------|----|
| `maximize`    |    |
| `metric_name` |    |
| `min_delta`   |    |
| `save_best`   |    |
| `data_name`   |    |
