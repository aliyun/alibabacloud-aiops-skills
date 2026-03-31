# Kafka Datasource Documentation

## Property Definition

- **Datasource Type**: `kafka`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode`, `UrlMode`

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "192.168.1.100", "port": "9092"}]` | Yes | Kafka connection address. |
| `version` | String | `2.0` | Yes | Client version. Only supports `"2.0"` or `"3.4"`. |
| `securityProtocol` | String | `authTypeNone` | Yes | Authentication method. Values:<br>• `authTypeNone`: No authentication<br>• `authTypeSaslSsl`: SASL SSL<br>• `authTypeSaslPlaintext`: SASL Plaintext<br>• `authTypeSsl`: SSL |
| `saslMechanism` | String | `plain` | Conditional | SASL mechanism. Required when `securityProtocol=authTypeSaslSsl` or `authTypeSaslPlaintext`. Values: `gssapi`, `plain`, `scram-sha-256`, `scram-sha-512`. |
| `saslUsername` | String | `user` | No | SASL username. |
| `saslPassword` | String | `xxx` | No | SASL password. |
| `truststoreFile` | String | `<FILE_ID>` | Conditional | Truststore certificate file ID. Required when `securityProtocol=authTypeSsl` or `authTypeSaslSsl`. |
| `truststorePassword` | String | `xxx` | No | Truststore password. |
| `keystoreFile` | String | `<FILE_ID>` | No | Keystore certificate file ID. |
| `keystorePassword` | String | `xxx` | No | Keystore password. |
| `keyPassword` | String | `xxx` | No | Private key password. |
| `kerberosFileKeytab` | String | `<FILE_ID>` | Conditional | Keytab authentication file. Required when using Kerberos. |
| `kerberosFileConf` | String | `<FILE_ID>` | Conditional | krb5.conf configuration file. Required when using Kerberos. |
| `jaasFileConf` | String | `<FILE_ID>` | No | JAAS configuration file. |
| `kafkaConfig` | JSON Object | `{}` | No | Kafka extended parameters. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## InstanceMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | Region where the instance belongs. |
| `instanceId` | String | `alikafka-xxxxx` | Yes | Kafka cluster ID. |
| `version` | String | `2.0` | Yes | Client version. Only supports `"2.0"` or `"3.4"`. |
| `securityProtocol` | String | `authTypeNone` | Yes | Authentication method. |
| `crossAccountOwnerId` | String | `<ACCOUNT_ID>` | No | Cross-account target Alibaba Cloud main account ID. |
| `crossAccountRoleName` | String | `role-name` | No | Cross-account role name. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### UrlMode (No Authentication)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "9092"}],
  "version": "2.0",
  "securityProtocol": "authTypeNone"
}
```

### UrlMode (SASL Plaintext)

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "9092"}],
  "version": "2.0",
  "securityProtocol": "authTypeSaslPlaintext",
  "saslMechanism": "plain",
  "saslUsername": "user",
  "saslPassword": "<PASSWORD>"
}
```

### InstanceMode

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "instanceId": "alikafka-xxxxx",
  "version": "2.0",
  "securityProtocol": "authTypeNone"
}
```
