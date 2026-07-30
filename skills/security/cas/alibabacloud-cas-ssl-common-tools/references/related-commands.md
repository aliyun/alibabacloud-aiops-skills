# Related CLI Commands

Consolidated reference of all CLI commands used by the SSL Certificate Toolkit.

## CAS (Certificate Authority Service)

| Command | Description | Used By |
|---------|-------------|---------|
| `aliyun cas list-instances` | List certificate instances with optional `--keyword` filter | Identity Resolver, Domain Verify, Certificate Upload |
| `aliyun cas get-instance-detail` | Get instance detail including cert content, status, validation method | Domain Verify, Certificate Download |
| `aliyun cas upload-user-certificate` | Upload third-party certificate (PEM) with `--Name`, `--Cert`, `--Key` | Certificate Upload |
| `aliyun cas get-task-attribute` | Poll async task result for domain verification | Domain Verify |
| `aliyun cas list-certificates` | List uploaded user certificates | Certificate Upload (duplicate check) |

## Alidns (Alibaba Cloud DNS)

| Command | Description | Used By |
|---------|-------------|---------|
| `aliyun alidns add-domain-record` | Add DNS record (TXT for domain verification) | Domain Verify |
| `aliyun alidns describe-domain-records` | Query existing DNS records for a domain | Domain Verify |
| `aliyun alidns describe-domains` | List all domains in DNS service | Domain Verify |

## STS (Security Token Service)

| Command | Description | Used By |
|---------|-------------|---------|
| `aliyun sts get-caller-identity` | Get current caller identity (AccountId, Arn, Type) | Identity Resolver |

## RAM (Resource Access Management)

| Command | Description | Used By |
|---------|-------------|---------|
| `aliyun ram get-role` | Check if a RAM role exists | Identity Resolver |
| `aliyun ram create-role` | Create a new RAM role with trust policy | Identity Resolver |
| `aliyun ram attach-policy-to-role` | Attach a permission policy to a role | Identity Resolver |

## Local Shell Scripts

| Script | Usage | Description |
|--------|-------|-------------|
| `scripts/split-chain.sh` | `./split-chain.sh <fullchain.pem> <output_dir>` | Split fullchain PEM into server cert + chain |
| `scripts/convert-format.sh` | `./convert-format.sh <command> [options]` | PEM/PFX/JKS/DER format conversion |
| `scripts/modulus-check.sh` | `./modulus-check.sh <type> <file1> <file2> [file3]` | Compare key/cert/CSR modulus |

## OpenSSL Commands

| Command | Description | Used By |
|---------|-------------|---------|
| `openssl req -new -newkey rsa:2048 -nodes -keyout <key> -out <csr> -subj "/CN=<domain>"` | Generate RSA CSR | CSR Generation |
| `openssl req -new -newkey rsa:2048 -nodes -keyout <key> -out <csr> -config <cnf> -extensions v3_req` | Generate multi-domain SAN CSR | CSR Generation |
| `openssl ecparam -genkey -name prime256v1 -out <key>` | Generate ECC private key | CSR Generation |
| `openssl req -new -key <key> -out <csr> -subj "/CN=<domain>"` | Generate CSR from existing key | CSR Generation |
| `openssl req -in <csr> -text -noout` | Inspect CSR content | CSR Generation |
| `openssl x509 -in <cert> -text -noout` | Parse certificate details | Certificate Upload, Certificate Matching |
| `openssl x509 -in <cert> -noout -dates` | Check certificate validity dates | Certificate Matching |
| `openssl verify -CAfile <chain> <cert>` | Verify certificate chain | Certificate Download, Certificate Matching |
| `openssl pkcs12 -export -out <pfx> -inkey <key> -in <cert> -certfile <chain>` | Convert PEM to PFX | Format Conversion |
| `openssl pkcs12 -in <pfx> -out <pem> -nodes` | Convert PFX to PEM | Format Conversion |
| `openssl x509 -outform DER -in <pem> -out <der>` | Convert PEM to DER | Format Conversion |
| `openssl x509 -inform DER -in <der> -out <pem>` | Convert DER to PEM | Format Conversion |
| `openssl rsa -in <key> -modulus -noout \| openssl md5` | Extract key modulus hash | Certificate Matching |
| `openssl x509 -in <cert> -modulus -noout \| openssl md5` | Extract cert modulus hash | Certificate Matching |
