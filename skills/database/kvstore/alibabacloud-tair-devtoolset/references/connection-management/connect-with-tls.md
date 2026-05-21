
## Connect With TLS

Connect to Tair instances with TLS (SSL) encryption to secure data in transit. Download the CA certificate (ApsaraDB-CA-Chain.pem or .jks) from the TLS encryption page.

### Proxy Connection Mode

Use these examples for standard architecture, cluster architecture with proxy mode, or read/write splitting architecture.

**Jedis (Java):**

```xml
<!-- Maven dependency -->
<dependency>
    <groupId>redis.clients</groupId>
    <artifactId>jedis</artifactId>
    <version>4.3.0</version>
</dependency>
```

```java
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.KeyStore;
import java.security.SecureRandom;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import org.apache.commons.pool2.impl.GenericObjectPoolConfig;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

public class JedisSSLTest {
    private static SSLSocketFactory createTrustStoreSSLSocketFactory(String jksFile) throws Exception {
        KeyStore trustStore = KeyStore.getInstance("jks");
        InputStream inputStream = null;
        try {
            inputStream = new FileInputStream(jksFile);
            trustStore.load(inputStream, null);
        } finally {
            inputStream.close();
        }

        TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance("PKIX");
        trustManagerFactory.init(trustStore);
        TrustManager[] trustManagers = trustManagerFactory.getTrustManagers();

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, trustManagers, new SecureRandom());
        return sslContext.getSocketFactory();
    }

    public static void main(String[] args) throws Exception {
        // ApsaraDB-CA-Chain.jks is the certificate file name
        final SSLSocketFactory sslSocketFactory = createTrustStoreSSLSocketFactory("ApsaraDB-CA-Chain.jks");
        // Configure the connection pool with the instance endpoint, port, timeout, and password
        JedisPool pool = new JedisPool(new GenericObjectPoolConfig(), 
            "r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com",
            6379, 2000, "redistest:Pas***23", 0, true, sslSocketFactory, null, null);

        try (Jedis jedis = pool.getResource()) {
            jedis.set("key", "value");
            System.out.println(jedis.get("key"));
        }
    }
}
```

**redis-py (Python):**

```python
#!/bin/python
# pip install redis
import redis

# Connection pool approach
# ApsaraDB-CA-Chain.pem is the certificate file name
pool = redis.ConnectionPool(
    connection_class=redis.connection.SSLConnection,
    max_connections=100,
    host="r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com",
    port=6379,
    password="redistest:Pas***23",
    ssl_cert_reqs=True,
    ssl_ca_certs="ApsaraDB-CA-Chain.pem"
)
client = redis.Redis(connection_pool=pool)
client.set("hi", "redis")
print(client.get("hi"))
```

```python
#!/bin/python
# pip install redis
import redis

# Standard connection approach
client = redis.Redis(
    host="r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com",
    port=6379,
    password="redistest:Test1234",
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs="ApsaraDB-CA-Chain.pem"
)

client.set("hello", "world")
print(client.get("hello"))
```

**Predis (PHP):**

```php
// composer require predis/predis
<?php

require __DIR__.'/predis/autoload.php';

/* ApsaraDB-CA-Chain.pem is the certificate file name
   Replace host, port, and password with your instance values */
$client = new Predis\Client([
    'scheme'   => 'tls',
    'host'     => 'r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com',
    'port'     => 6379,
    'password' => 'redistest:Pas***23',
    'ssl'      => ['cafile' => 'ApsaraDB-CA-Chain.pem', 'verify_peer' => true],
]);

$client->set("hello", "world");
print $client->get("hello")."\n";

?>
```

**StackExchange.Redis (C#):**

```csharp
// Install-Package StackExchange.Redis
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
using StackExchange.Redis;

namespace SSLTest
{
    class Program
    {
        private static bool CheckServerCertificate(object sender, X509Certificate certificate,
            X509Chain chain, SslPolicyErrors sslPolicyErrors)
        {
            var ca = new X509Certificate2(
                "/your path/ApsaraDB-CA-Chain/ApsaraDB-CA-Chain.pem");
            return chain.ChainElements
                .Cast<X509ChainElement>()
                .Any(x => x.Certificate.Thumbprint == ca.Thumbprint);
        }

        static void Main(string[] args)
        {
            // ApsaraDB-CA-Chain.pem is the certificate file name
            ConfigurationOptions config = new ConfigurationOptions()
            {
                EndPoints = {"r-bp10q23zyfriodu****.redis.rds.aliyuncs.com:6379"},
                Password = "redistest:Pas***23",
                Ssl = true,
            };

            config.CertificateValidation += CheckServerCertificate;
            using (var conn = ConnectionMultiplexer.Connect(config))
            {
                Console.WriteLine("connected");
                var db = conn.GetDatabase();
                db.StringSet("hello", "world");
                Console.WriteLine(db.StringGet("hello"));
            }
        }
    }
}
```

**Spring Data Redis (Java):**

```java
// Spring Data Redis 2.7.12 or later
@Configuration
public class RedisConfig {
    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        // Store TLS certificate configuration in a properties file for production use
        String host = "r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com";
        int port = 6379;
        String password = "Pas***23";
        String trustStoreFilePath = "/path/to/ApsaraDB-CA-Chain.jks";

        ClientOptions clientOptions = ClientOptions.builder().sslOptions(
            SslOptions.builder().jdkSslProvider().truststore(new File(trustStoreFilePath)).build()).build();
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName(host);
        config.setPort(port);
        config.setPassword(password);
        LettuceClientConfiguration lettuceClientConfiguration = LettuceClientConfiguration.builder()
            .clientOptions(clientOptions)
            .useSsl().build();
        return new LettuceConnectionFactory(config, lettuceClientConfiguration);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> redisTemplate = new RedisTemplate<>();
        redisTemplate.setConnectionFactory(redisConnectionFactory);
        return redisTemplate;
    }
}
```

**Lettuce (Java):**

```java
// Lettuce 6.2.4.RELEASE or later
public class SSLExample {
    public static void main(String[] args) throws Exception {
        String host = "r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com";
        int port = 6379;
        String password = "Pas***23";
        String trustStoreFilePath = "/path/to/ApsaraDB-CA-Chain.jks";

        RedisURI uri = RedisURI.builder()
            .withHost(host)
            .withPort(port)
            .withPassword(password.toCharArray())
            .withSsl(true).build();

        SslOptions sslOptions = SslOptions.builder()
            .jdkSslProvider()
            .truststore(new File(trustStoreFilePath)).build();

        ClientOptions clientOptions = ClientOptions.builder()
            .sslOptions(sslOptions).build();
        RedisClient client = RedisClient.create(uri);
        client.setOptions(clientOptions);

        RedisCommands<String, String> sync = client.connect().sync();
        System.out.println(sync.set("key", "value"));
        System.out.println(sync.get("key"));
    }
}
```

**go-redis (Go):**

```go
// go get github.com/redis/go-redis/v9
package main

import (
    "context"
    "fmt"
    "io/ioutil"
    "crypto/tls"
    "crypto/x509"
    "github.com/redis/go-redis/v9"
)

var ctx = context.Background()

func main() {
    caCert, err := ioutil.ReadFile("/root/ApsaraDB-CA-Chain.pem")
    if err != nil {
        fmt.Println("Error loading CA certificate:", err)
        return
    }

    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    tlsConfig := &tls.Config{
        RootCAs:            caCertPool,
        InsecureSkipVerify: true,  // Skip hostname verification, CA still validated
    }

    rdb := redis.NewClient(&redis.Options{
        Addr:      "r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com:6379",
        Password:  "redistest:Pas***23",
        TLSConfig: tlsConfig,
    })

    err = rdb.Set(ctx, "key", "value", 0).Err()
    if err != nil {
        panic(err)
    }

    val, err := rdb.Get(ctx, "key").Result()
    if err != nil {
        panic(err)
    }
    fmt.Println("key =", val)
}
```

**redis-cli:**

```shell
# Build redis-cli with TLS support
sudo yum -y install openssl-devel gcc
wget --timeout=60 https://download.redis.io/releases/redis-7.2.0.tar.gz
tar xzf redis-7.2.0.tar.gz
cd redis-7.2.0 && make BUILD_TLS=yes

# Connect with TLS, specifying the CA certificate path
./src/redis-cli -h r-bp14joyeihew30****.redis.rds.aliyuncs.com -p 6379 --tls --cacert ./ApsaraDB-CA-Chain.pem

# Authenticate
AUTH password
```

### Direct Connection Mode

Use these examples for cluster architecture with direct connection mode enabled.

**JedisCluster (Java):**

```xml
<!-- Maven dependency -->
<dependency>
    <groupId>redis.clients</groupId>
    <artifactId>jedis</artifactId>
    <version>4.3.0</version>
</dependency>
```

```java
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.util.HashSet;
import java.util.Set;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import redis.clients.jedis.ConnectionPoolConfig;
import redis.clients.jedis.DefaultJedisClientConfig;
import redis.clients.jedis.HostAndPort;
import redis.clients.jedis.JedisCluster;

public class JedisClusterTSL {
    private static final int DEFAULT_TIMEOUT = 2000;
    private static final int DEFAULT_REDIRECTIONS = 5;
    private static final ConnectionPoolConfig jedisPoolConfig = new ConnectionPoolConfig();

    private static SSLSocketFactory createTrustStoreSSLSocketFactory(String jksFile) throws Exception {
        KeyStore trustStore = KeyStore.getInstance("jks");
        InputStream inputStream = null;
        try {
            inputStream = new FileInputStream(jksFile);
            trustStore.load(inputStream, null);
        } finally {
            inputStream.close();
        }

        TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance("PKIX");
        trustManagerFactory.init(trustStore);
        TrustManager[] trustManagers = trustManagerFactory.getTrustManagers();

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, trustManagers, new SecureRandom());
        return sslContext.getSocketFactory();
    }

    public static void main(String args[]) throws Exception {
        // In direct connection mode, keep (business machines × MaxTotal) below the per-shard connection limit
        jedisPoolConfig.setMaxTotal(30);
        jedisPoolConfig.setMaxIdle(30);
        jedisPoolConfig.setMinIdle(15);

        int port = 6379;
        String host = "r-2zee50zxi5iiq****.redis.rds-aliyun.rds.aliyuncs.com";
        String user = "default";
        String password = "Pas***23";

        final SSLSocketFactory sslSocketFactory = createTrustStoreSSLSocketFactory("/root/ApsaraDB-CA-Chain.jks");
        DefaultJedisClientConfig jedisClientConfig = DefaultJedisClientConfig.builder()
            .connectionTimeoutMillis(DEFAULT_TIMEOUT)
            .socketTimeoutMillis(DEFAULT_TIMEOUT)
            .user(user).password(password)
            .ssl(true)
            .sslSocketFactory(sslSocketFactory).build();

        Set<HostAndPort> jedisClusterNode = new HashSet<HostAndPort>();
        jedisClusterNode.add(new HostAndPort(host, port));
        JedisCluster jc = new JedisCluster(jedisClusterNode, jedisClientConfig, DEFAULT_REDIRECTIONS, jedisPoolConfig);
        System.out.println(jc.set("key", "value"));
        System.out.println(jc.get("key"));

        jc.close();  // Call when the application exits to release resources
    }
}
```

**redis-py Cluster (Python):**

```python
#!/usr/bin/env python
# pip install redis
from redis.cluster import RedisCluster

# Replace host and port with your instance endpoint and port
host = 'r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com'
port = 6379
# Replace user and pwd with your instance account and password
user = 'default'
pwd = 'Pas***23'

rc = RedisCluster(host=host, port=port, username=user, password=pwd,
                  ssl=True, ssl_ca_certs="/root/ApsaraDB-CA-Chain.pem")
rc.set('foo', 'bar')
print(rc.get('foo'))
```

**phpredis Cluster (PHP):**

```php
// pecl install redis
<?php
// Direct connection endpoint and port
$array = ['r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com:6379'];
// Connection password
$pwd = "Pas***23";
// TLS settings
$tls = ["verify_peer" => false, "verify_peer_name" => false];
// Connect to the cluster
$obj_cluster = new RedisCluster(NULL, $array, 1.5, 1.5, true, $pwd, $tls);
var_dump($obj_cluster);

if ($obj_cluster->set("foo", "bar") == false) {
    die($obj_cluster->getLastError());
}
$value = $obj_cluster->get("foo");
echo $value;
echo "\n";
?>
```

**StackExchange.Redis Cluster (C#):**

```csharp
// Install-Package StackExchange.Redis
using StackExchange.Redis;
using System;
using System.Linq;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;

namespace TairClient
{
    class Program
    {
        static void Main()
        {
            const string Host = "r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com";
            const int Port = 6379;
            Console.WriteLine("connecting...");
            var config = new ConfigurationOptions
            {
                EndPoints = { { Host, Port } },
                Ssl = true,
                Password = "Pas***23",
            };
            config.CertificateValidation += (sender, cert, chain, errors) =>
            {
                if (errors == SslPolicyErrors.RemoteCertificateChainErrors ||
                    errors == SslPolicyErrors.RemoteCertificateNameMismatch)
                {
                    return true;
                }
                var caCert = LoadCertificateFromPem("/root/ApsaraDB-CA-Chain.pem");
                var isCertIssuedByTrustedCA = chain.ChainElements
                    .Cast<X509ChainElement>()
                    .Any(x => x.Certificate.Thumbprint.Equals(
                        caCert.Thumbprint, StringComparison.OrdinalIgnoreCase));
                return isCertIssuedByTrustedCA;
            };

            using (var conn = ConnectionMultiplexer.Connect(config))
            {
                Console.WriteLine("connected");
                var db = conn.GetDatabase();
                db.StringSet("hello", "world");
                Console.WriteLine(db.StringGet("hello")); // world
            }
        }

        private static X509Certificate2 LoadCertificateFromPem(string pemFilePath)
        {
            X509Certificate2 cert = X509Certificate2.CreateFromPem(File.ReadAllText(pemFilePath));
            return cert;
        }
    }
}
```

**Spring Data Redis Cluster - Jedis (Java):**

```java
// Spring Data Redis 2.7.5 or later
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.List;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisClusterConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.jedis.JedisClientConfiguration;
import org.springframework.data.redis.connection.jedis.JedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import redis.clients.jedis.JedisPoolConfig;

@Configuration
public class RedisConfigJedis {
    private static SSLSocketFactory createTrustStoreSSLSocketFactory(String jksFile) throws Exception {
        KeyStore trustStore = KeyStore.getInstance("jks");
        InputStream inputStream = null;
        try {
            inputStream = new FileInputStream(jksFile);
            trustStore.load(inputStream, null);
        } finally {
            inputStream.close();
        }

        TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance("PKIX");
        trustManagerFactory.init(trustStore);
        TrustManager[] trustManagers = trustManagerFactory.getTrustManagers();

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, trustManagers, new SecureRandom());
        return sslContext.getSocketFactory();
    }

    @Bean
    public RedisConnectionFactory redisConnectionFactory() throws Exception {
        String host = "r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com:6379";
        String user = "default";
        String password = "Pas***23";
        String trustStoreFilePath = "/root/ApsaraDB-CA-Chain.jks";

        List<String> clusterNodes = Arrays.asList(host);
        RedisClusterConfiguration redisClusterConfiguration = new RedisClusterConfiguration(clusterNodes);
        redisClusterConfiguration.setUsername(user);
        redisClusterConfiguration.setPassword(password);

        JedisPoolConfig jedisPoolConfig = new JedisPoolConfig();
        // In direct connection mode, keep (business machines × MaxTotal) below the per-shard connection limit
        jedisPoolConfig.setMaxTotal(30);
        jedisPoolConfig.setMaxIdle(20);
        jedisPoolConfig.setMinIdle(20);

        final SSLSocketFactory sslSocketFactory = createTrustStoreSSLSocketFactory(trustStoreFilePath);
        JedisClientConfiguration jedisClientConfiguration = JedisClientConfiguration.builder()
            .useSsl().sslSocketFactory(sslSocketFactory)
            .and().usePooling().poolConfig(jedisPoolConfig).build();

        return new JedisConnectionFactory(redisClusterConfiguration, jedisClientConfiguration);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> redisTemplate = new RedisTemplate<>();
        redisTemplate.setConnectionFactory(redisConnectionFactory);
        return redisTemplate;
    }
}
```

**Spring Data Redis Cluster - Lettuce (Java):**

```java
// Spring Data Redis 2.7.5 or later
import java.io.File;
import io.lettuce.core.ClientOptions;
import io.lettuce.core.SslOptions;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisClusterConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;

@Configuration
public class RedisConfig {
    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        String host = "r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com";
        int port = 6379;
        String user = "default";
        String password = "Pas***23";
        String trustStoreFilePath = "/root/ApsaraDB-CA-Chain.jks";

        ClientOptions clientOptions = ClientOptions.builder().sslOptions(
            SslOptions.builder().jdkSslProvider().truststore(new File(trustStoreFilePath)).build()).build();
        RedisClusterConfiguration clusterConfiguration = new RedisClusterConfiguration();
        clusterConfiguration.clusterNode(host, port);
        clusterConfiguration.setUsername(user);
        clusterConfiguration.setPassword(password);

        LettuceClientConfiguration lettuceClientConfiguration = LettuceClientConfiguration.builder()
            .clientOptions(clientOptions)
            .useSsl()
            .disablePeerVerification()
            .build();
        return new LettuceConnectionFactory(clusterConfiguration, lettuceClientConfiguration);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> redisTemplate = new RedisTemplate<>();
        redisTemplate.setConnectionFactory(redisConnectionFactory);
        return redisTemplate;
    }
}
```

**Lettuce Cluster (Java):**

```java
// Lettuce 6.3.0.RELEASE or later
import java.io.File;
import java.time.Duration;
import io.lettuce.core.RedisURI;
import io.lettuce.core.SocketOptions;
import io.lettuce.core.SocketOptions.KeepAliveOptions;
import io.lettuce.core.SocketOptions.TcpUserTimeoutOptions;
import io.lettuce.core.SslOptions;
import io.lettuce.core.SslVerifyMode;
import io.lettuce.core.cluster.ClusterClientOptions;
import io.lettuce.core.cluster.ClusterTopologyRefreshOptions;
import io.lettuce.core.cluster.RedisClusterClient;
import io.lettuce.core.cluster.api.StatefulRedisClusterConnection;

public class SSLClusterExample {
    /**
     * TCP keepalive settings:
     * TCP_KEEPIDLE = 30s, TCP_KEEPINTVL = 10s, TCP_KEEPCNT = 3
     */
    private static final int TCP_KEEPALIVE_IDLE = 30;

    /**
     * TCP_USER_TIMEOUT prevents Lettuce from hanging indefinitely on broken connections.
     * See: https://github.com/lettuce-io/lettuce-core/issues/2082
     */
    private static final int TCP_USER_TIMEOUT = 30;

    public static void main(String[] args) throws Exception {
        String host = "r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com";
        int port = 6379;
        String password = "Pas***23";
        String trustStoreFilePath = "/root/ApsaraDB-CA-Chain.jks";

        RedisURI uri = RedisURI.builder()
            .withHost(host)
            .withPort(port)
            .withPassword(password.toCharArray())
            .withSsl(true)
            // Direct cluster connections require CA-only verification; FULL mode is not supported.
            .withVerifyPeer(SslVerifyMode.CA)
            .build();

        SslOptions sslOptions = SslOptions.builder()
            .jdkSslProvider()
            .truststore(new File(trustStoreFilePath)).build();

        ClusterTopologyRefreshOptions refreshOptions = ClusterTopologyRefreshOptions.builder()
            .enablePeriodicRefresh(Duration.ofSeconds(15))
            .dynamicRefreshSources(false)
            .enableAllAdaptiveRefreshTriggers()
            .adaptiveRefreshTriggersTimeout(Duration.ofSeconds(15)).build();

        SocketOptions socketOptions = SocketOptions.builder()
            .keepAlive(KeepAliveOptions.builder()
                .enable()
                .idle(Duration.ofSeconds(TCP_KEEPALIVE_IDLE))
                .interval(Duration.ofSeconds(TCP_KEEPALIVE_IDLE / 3))
                .count(3)
                .build())
            .tcpUserTimeout(TcpUserTimeoutOptions.builder()
                .enable()
                .tcpUserTimeout(Duration.ofSeconds(TCP_USER_TIMEOUT))
                .build())
            .build();

        RedisClusterClient redisClient = RedisClusterClient.create(uri);
        redisClient.setOptions(ClusterClientOptions.builder()
            .socketOptions(socketOptions)
            .sslOptions(sslOptions)
            .validateClusterNodeMembership(false)
            .topologyRefreshOptions(refreshOptions).build());

        StatefulRedisClusterConnection<String, String> connection = redisClient.connect();
        connection.sync().set("key", "value");
        System.out.println(connection.sync().get("key"));
    }
}
```

**go-redis Cluster (Go):**

```go
// go get github.com/redis/go-redis/v9
package main

import (
    "context"
    "fmt"
    "io/ioutil"
    "crypto/tls"
    "crypto/x509"
    "github.com/redis/go-redis/v9"
)

var ctx = context.Background()

func main() {
    caCert, err := ioutil.ReadFile("/root/ApsaraDB-CA-Chain.pem")
    if err != nil {
        fmt.Println("Error loading CA certificate:", err)
        return
    }

    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    tlsConfig := &tls.Config{
        RootCAs:            caCertPool,
        InsecureSkipVerify: true, // Not actually skipping — cert is verified in VerifyPeerCertificate
        VerifyPeerCertificate: func(rawCerts [][]byte, verifiedChains [][]*x509.Certificate) error {
            // Validate the CA chain while skipping hostname verification.
            // Reference: https://github.com/golang/go/issues/21971#issuecomment-412836078
            certs := make([]*x509.Certificate, len(rawCerts))
            for i, asn1Data := range rawCerts {
                cert, err := x509.ParseCertificate(asn1Data)
                if err != nil {
                    panic(err)
                }
                certs[i] = cert
            }

            opts := x509.VerifyOptions{
                Roots:         caCertPool,
                DNSName:       "", // Skip hostname verification
                Intermediates: x509.NewCertPool(),
            }

            for i, cert := range certs {
                if i == 0 {
                    continue
                }
                opts.Intermediates.AddCert(cert)
            }
            _, err := certs[0].Verify(opts)
            return err
        },
    }

    rdb := redis.NewClusterClient(&redis.ClusterOptions{
        Addrs:     []string{"r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com:6379"},
        Username:  "default",
        Password:  "Pas***23",
        TLSConfig: tlsConfig,
    })

    err = rdb.Set(ctx, "key", "value", 0).Err()
    if err != nil {
        panic(err)
    }

    val, err := rdb.Get(ctx, "key").Result()
    if err != nil {
        panic(err)
    }
    fmt.Println("key =", val)
}
```

**redis-cli Cluster:**

```shell
# Build redis-cli with TLS support
sudo yum -y install openssl-devel gcc
wget --timeout=60 https://download.redis.io/releases/redis-7.2.0.tar.gz
tar xzf redis-7.2.0.tar.gz
cd redis-7.2.0 && make BUILD_TLS=yes

# Connect with TLS and cluster mode (-c)
./src/redis-cli -h r-2zee50zxi5iiqm****.redis.rds-aliyun.rds.aliyuncs.com -p 6379 --tls --cacert ./ApsaraDB-CA-Chain.pem -c

# Authenticate
AUTH password
```

**Reference:** [Connect to Redis and Tair instances with TLS encryption](https://help.aliyun.com/en/redis/user-guide/use-a-client-to-connect-to-an-apsaradb-for-redis-instance-that-has-ssl-encryption-enabled)
