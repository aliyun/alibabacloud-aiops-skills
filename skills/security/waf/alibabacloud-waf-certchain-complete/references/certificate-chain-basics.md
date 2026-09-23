# Certificate Chain Basics

## What is a Certificate Chain?

A certificate chain is a sequence of certificates that establishes trust from the server certificate to a root CA certificate:

```
Root CA Certificate (self-signed, trusted by browsers)
    └── Intermediate CA Certificate(s) (signed by Root or another Intermediate)
        └── Server Certificate (signed by Intermediate, contains domain name)
```

## Why the Incomplete Certificate Chain Message Appears

The WAF console shows an "incomplete certificate chain" message when the uploaded certificate is missing intermediate certificates. Common causes:

1. **User uploaded only the server certificate**: The most common cause. Users often download only the domain certificate from their CA portal and upload it to WAF without including the intermediate certificates.

2. **CA portal provided separate files**: Some CAs provide the server certificate and intermediate certificates as separate files. Users need to concatenate them.

3. **Copy-paste errors**: When copying certificate content, extra whitespace or missing `-----END CERTIFICATE-----` lines can break the chain.

4. **Let's Encrypt cert.pem vs fullchain.pem**: Let's Encrypt issues two files — `cert.pem` (server cert only) and `fullchain.pem` (complete chain). Users must use `fullchain.pem`.

## Complete vs Incomplete Chain

### Complete Chain (correct)

```
-----BEGIN CERTIFICATE-----
(Server certificate for example.com)
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
(Intermediate CA certificate)
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
(Root CA certificate - optional, browsers have it built-in)
-----END CERTIFICATE-----
```

### Incomplete Chain (incorrect)

```
-----BEGIN CERTIFICATE-----
(Server certificate for example.com)
-----END CERTIFICATE-----
(missing intermediate certificate!)
```

## How to Fix

### Quick Fix Steps

1. Identify the issuing CA from the server certificate:
   ```bash
   openssl x509 -in server_cert.pem -noout -issuer
   ```

2. Download the intermediate certificate from the CA's website

3. Concatenate: server cert + intermediate(s):
   ```bash
   cat server_cert.pem intermediate.pem > fullchain.pem
   ```

4. Verify the chain:
   ```bash
   openssl verify -untrusted intermediate.pem server_cert.pem
   ```

5. Upload `fullchain.pem` to WAF

### Auto-Fix with Script

```bash
python3 scripts/fix_certchain.py \
  --file server_cert.pem \
  --fix \
  --output fullchain.pem
python3 scripts/fix_certchain.py --file fullchain.pem
```

## Common CA Intermediate Certificate Sources

| CA | Intermediate Portal |
|----|-------------------|
| DigiCert | https://www.digicert.com/kb/digicert-root-certificates/ |
| Let's Encrypt | https://letsencrypt.org/certificates/ |
| GlobalSign | https://support.globalsign.com/ca-certificates/intermediate-certificates |
| Sectigo | https://www.sectigo.com/knowledge-article/detail/Sectigo-Intermediate-Certificates |
| GeoTrust | https://www.geotrust.com/resources/root-certificates/ |
| Comodo | https://www.sectigo.com/knowledge-article/detail/Sectigo-Intermediate-Certificates |

## Key OpenSSL Concepts

- **AIA (Authority Information Access)**: An X.509 extension in the server certificate that contains the URL where the issuing CA's intermediate certificate can be downloaded. Extract with `openssl x509 -in cert.pem -noout -ext authorityInfoAccess`.

- **Subject/Issuer chain**: Each certificate's Issuer field should match the next certificate's Subject field in the chain.

- **Self-signed root**: The root CA certificate is self-signed (Subject == Issuer). Browsers have root certificates pre-installed, so including the root in the chain is optional.
