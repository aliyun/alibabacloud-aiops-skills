# FTP Data Source Connection Properties Documentation

## Overview

- **Data Source Type**: `ftp`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `protocol` | String | `ftp` | Yes | Protocol type. Valid values: `ftp`, `sftp`, `ftps`. |
| `host` | String | `10.0.0.1` | Yes | Host address. |
| `port` | String | `22` | Yes | Port number. |
| `baseDir` | String | `/root/` | No | Base path/directory. |
| `securityProtocol` | String | `passwordAuth` | No | Required when using SFTP protocol. Authentication option, valid values: `passwordAuth`, `authTypeSshKey`. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | No | Password. Required when: protocol is SFTP with `passwordAuth` authentication, or protocol is FTP/FTPS. |
| `sshKeyFile` | String | `1` | No | Authentication file ID. Required when authentication option is `authTypeSshKey`. |

---

## Configuration Example

### Connection String Mode

```json
{
  "host": "127.0.0.1",
  "port": "5432",
  "protocol": "sftp",
  "securityProtocol": "passwordAuth",
  "username": "xxxxx",
  "password": "xxxxx",
  "envType": "Dev"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/ftp*

*Last Updated: 2024-10-17*
