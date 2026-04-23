# Access and installation

## Enable MaxFrame for your MaxCompute project

You need to setup a MaxCompute project Before using MaxFrame. Please take a look at
[here](https://www.alibabacloud.com/zh/product/maxcompute) for more information.

#### NOTE
Currently MaxFrame is under trial. If you need to enable MaxFrame for your MaxCompute
project, please [fill the form to apply for trial](https://survey.aliyun.com/apps/zhiliao/m40AIrxhA?spm=a2c4g.11186623.0.0.a69340f2mJENKJ) here.

## Install MaxFrame client locally

After created your own MaxCompute project and enabled MaxFrame, you may install
MaxFrame client with pip command:

```bash
pip install maxframe
```

Then you can create a MaxCompute table, perform some transformation with MaxFrame
and then store the result into another MaxCompute table.

```python
import maxframe.dataframe as md
from odps import ODPS
from maxframe import new_session

# create MaxCompute entrance object and test table
o = ODPS(
    access_id=os.getenv('ODPS_ACCESS_ID'),
    secret_access_key=os.getenv('ODPS_ACCESS_KEY'),
    project='your-default-project',
    endpoint='your-end-point',
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)
table = o.create_table("test_source_table", "a string, b bigint")
with table.open_writer() as writer:
    writer.write([
        ["value1", 0],
        ["value2", 1],
    ])

# create maxframe session
session = new_session(o)

# perform data transformation
df = md.read_odps_table("test_source_table")
df["a"] = "prefix_" + df["a"]
md.to_odps_table(df, "test_prefix_source_table").execute()

# destroy maxframe session
session.destroy()
```

## Access MaxFrame with DataWorks

DataWorks provides task scheduling capability for MaxCompute projects. You can schedule
and run MaxFrame job with DataWorks.

To run MaxFrame job with DataWorks, you need to create a PyODPS 3 node and write your code
inside it. PyODPS nodes are executed with embedded MaxCompute accounts and project information,
thus you may create your MaxFrame session directly.

```python
import maxframe.dataframe as md
from maxframe import new_session

# create maxframe session
session = new_session(o)

# perform data transformation
df = md.read_odps_table("test_source_table")
df["a"] = "prefix_" + df["a"]
md.to_odps_table(df, "test_prefix_source_table").execute()

# destroy maxframe session
session.destroy()
```

## Access MaxFrame with MaxCompute Notebook

[MaxCompute Notebook](https://help.aliyun.com/zh/maxcompute/user-guide/maxcompute-notebook-instruction)
also provides MaxFrame package. It also provides MaxCompute account in environment variables
in the notebook, thus account information is not needed.

```python
import maxframe.dataframe as md
from maxframe import new_session

# create MaxCompute entrance object
o = ODPS(
    project='your-default-project',
    endpoint='your-end-point',
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)
# create maxframe session
session = new_session(o)

# perform data transformation
df = md.read_odps_table("test_source_table")
df["a"] = "prefix_" + df["a"]
md.to_odps_table(df, "test_prefix_source_table").execute()

# destroy maxframe session
session.destroy()
```
