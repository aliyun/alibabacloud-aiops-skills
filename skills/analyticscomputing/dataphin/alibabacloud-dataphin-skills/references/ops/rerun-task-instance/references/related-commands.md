# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public --help` | 查看全部命令 |
| `aliyun dataphin-public list-projects` | 枚举项目 |
| `aliyun dataphin-public list-instances` | 按任务名/节点/业务日期查询实例 |
| `aliyun dataphin-public operate-instance` | 批量运维实例：RERUN / PAUSE / RESUME / TERMINATE / SET_SUCCESS（模式①） |
| `aliyun dataphin-public fix-data` | 重跑下游链路（修复链路数据），联动重跑根实例及所有下游（模式②） |
| `aliyun dataphin-public get-physical-instance` | 查询单个实例信息 |
| `aliyun dataphin-public get-physical-instance-log` | 获取实例运行日志（fix-data 验证核心命令：查 taskrun 数量） |
| `aliyun dataphin-public get-instance-down-stream` | 查询实例下游拓扑（模式②辅助：获取下游实例 ID 列表） |
| `aliyun dataphin-public get-instance-up-down-stream` | 查询实例上下游（模式②辅助） |
| `aliyun dataphin-public list-nodes` | 按任务名查节点 ID（备用） |
