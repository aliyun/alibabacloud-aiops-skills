# RAM Permissions

**This skill requires no Alibaba Cloud RAM permissions.**

All cluster access goes through the bundled `srsql` CLI, which speaks the
MySQL wire protocol (port 9030) to the StarRocks FE using a
StarRocks-internal account (FE user/password). The skill does not call any
Alibaba Cloud OpenAPI, does not assume a RAM role, and does not read
`aliyun configure` / AccessKey credentials.

Privileges are evaluated entirely inside StarRocks via
`SHOW GRANTS FOR CURRENT_USER()`. See [connect.md](connect.md) for the
auth and security model.
