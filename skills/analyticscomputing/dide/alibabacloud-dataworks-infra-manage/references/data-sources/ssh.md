# SSH Datasource Documentation

## Property Definition

- **Datasource Type**: `ssh`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `host` | String | `192.168.1.100` | Yes | Host address. |
| `port` | String | `22` | Yes | Host port. |
| `username` | String | `root` | Yes | Username. |
| `securityProtocol` | String | `passwordAuth` | Yes | Authentication mode. Values:<br>• `passwordAuth`: Password authentication<br>• `authTypeSshKey`: SSH key authentication<br>• `authTypeSshPublicKey`: Public key authentication |
| `password` | String | `xxx` | Conditional | Password. Required when `securityProtocol=passwordAuth`. |
| `sshKeyFile` | String | `<FILE_ID>` | Conditional | Private key file ID. Required when `securityProtocol=authTypeSshKey` or `authTypeSshPublicKey`. |
| `sshKeyPassword` | String | `xxx` | No | Private key password. Only available when `securityProtocol=authTypeSshKey`. |
| `publicKey` | String | `ssh-rsa xxx` | Conditional | Public key text. Required and read-only when `securityProtocol=authTypeSshPublicKey`. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### Password Authentication Mode

```json
{
  "envType": "Prod",
  "host": "192.168.1.100",
  "port": "22",
  "username": "root",
  "securityProtocol": "passwordAuth",
  "password": "<PASSWORD>"
}
```

### SSH Key Authentication Mode

```json
{
  "envType": "Prod",
  "host": "192.168.1.100",
  "port": "22",
  "username": "root",
  "securityProtocol": "authTypeSshKey",
  "sshKeyFile": "<FILE_ID>",
  "sshKeyPassword": "<PASSWORD>"
}
```

### SSH Public Key Authentication Mode

```json
{
  "envType": "Prod",
  "host": "192.168.1.100",
  "port": "22",
  "username": "root",
  "securityProtocol": "authTypeSshPublicKey",
  "sshKeyFile": "<FILE_ID>",
  "publicKey": "ssh-rsa xxxxx"
}
```
