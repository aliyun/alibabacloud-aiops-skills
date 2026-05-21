
## Connect Cluster

Connect to Tair cluster architecture instances using direct connection mode (private endpoint) with Redis Cluster protocol compatible clients.

### Client Examples

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
import redis.clients.jedis.*;
import java.util.HashSet;
import java.util.Set;

public class DirectTest {
    private static final int DEFAULT_TIMEOUT = 2000;
    private static final int DEFAULT_REDIRECTIONS = 5;
    private static final ConnectionPoolConfig config = new ConnectionPoolConfig();

    public static void main(String args[]) {
        // Specify the maximum number of connections
        // In direct connection mode: Number of clients × MaxTotal < Max connections per shard
        config.setMaxTotal(30);
        config.setMaxIdle(20);
        config.setMinIdle(15);

        // Specify the private endpoint allocated to the cluster instance
        String host = "r-bp1xxxxxxxxxxxx.redis.rds.aliyuncs.com";
        int port = 6379;
        // Specify the password used to connect to the cluster instance
        String password = "xxxxx";

        Set<HostAndPort> jedisClusterNode = new HashSet<HostAndPort>();
        jedisClusterNode.add(new HostAndPort(host, port));
        JedisCluster jc = new JedisCluster(jedisClusterNode, DEFAULT_TIMEOUT, DEFAULT_TIMEOUT, 
            DEFAULT_REDIRECTIONS, password, "clientName", config);

        jc.set("key", "value");
        jc.get("key");

        jc.close();  // Destroy resources when application exits
    }
}
```

**redis-py (Python):**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pip install redis
from redis.cluster import RedisCluster

# Replace the values of the host and port parameters with the endpoint and port
host = 'r-bp10noxlhcoim2****.redis.rds.aliyuncs.com'
port = 6379
# Replace the values of the user and pwd parameters with the username and password
user = 'testaccount'
pwd = 'Rp829dlwa'

rc = RedisCluster(host=host, port=port, username=user, password=pwd)
# You can perform operations after the connection is established
rc.set('foo', 'bar')
print(rc.get('foo'))
```

**PhpRedis (PHP):**

```php
// Install: pecl install redis
<?php
// Specify the private endpoint and port number
$array = ['r-bp1xxxxxxxxxxxx.redis.rds.aliyuncs.com:6379'];
// Specify the password used to connect to the cluster instance
$pwd = "xxxx";

// Use the password to connect to the cluster instance
$obj_cluster = new RedisCluster(NULL, $array, 1.5, 1.5, true, $pwd);

// Display the result of the connection
var_dump($obj_cluster);

if ($obj_cluster->set("foo", "bar") == false) {
    die($obj_cluster->getLastError());
}
$value = $obj_cluster->get("foo");
echo $value;
?>
```

**Spring Data Redis (Java):**

```xml
<!-- Maven pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>2.4.2</version>
        <relativePath/>
    </parent>
    <groupId>com.aliyun.tair</groupId>
    <artifactId>spring-boot-example</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <properties>
        <java.version>1.8</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
        </dependency>
        <dependency>
            <groupId>redis.clients</groupId>
            <artifactId>jedis</artifactId>
        </dependency>
    </dependencies>
</project>
```

```java
// Spring Data Redis Cluster Configuration
@Configuration
public class RedisClusterConfig {
    @Bean
    public RedisClusterConfiguration redisClusterConfiguration() {
        // Specify the private endpoint
        RedisClusterConfiguration clusterConfig = new RedisClusterConfiguration(
            Arrays.asList("r-bp1xxxxxxxxxxxx.redis.rds.aliyuncs.com:6379")
        );
        // Password format: account:password
        clusterConfig.setPassword("testaccount:Rp829dlwa");
        return clusterConfig;
    }

    @Bean
    public JedisConnectionFactory redisConnectionFactory() {
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(30);
        poolConfig.setMaxIdle(20);
        poolConfig.setTestOnBorrow(false);
        poolConfig.setTestOnReturn(false);

        JedisClientConfiguration clientConfig = JedisClientConfiguration.builder()
            .usePooling().poolConfig(poolConfig).build();

        return new JedisConnectionFactory(redisClusterConfiguration(), clientConfig);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate() {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(redisConnectionFactory());
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }
}
```

**ioredis (Node.js):**

```javascript
// npm install ioredis
const Redis = require('ioredis');

// Connect to cluster using private endpoint
const cluster = new Redis.Cluster([
    {
        host: 'r-bp1xxxxxxxxxxxx.redis.rds.aliyuncs.com',
        port: 6379
    }
], {
    redisOptions: {
        password: 'testaccount:Rp829dlwa'  // account:password format
    }
});

cluster.set('foo', 'bar', (err, result) => {
    if (err) {
        console.error(err);
        return;
    }
    console.log('Set result:', result);
});

cluster.get('foo', (err, result) => {
    if (err) {
        console.error(err);
        return;
    }
    console.log('Get result:', result);
});
```

**go-redis (Go):**

```go
// go get github.com/redis/go-redis/v9
package main

import (
    "context"
    "fmt"
    "github.com/redis/go-redis/v9"
)

func main() {
    ctx := context.Background()

    // Connect to cluster using private endpoint
    rdb := redis.NewClusterClient(&redis.ClusterOptions{
        Addrs:    []string{"r-bp1xxxxxxxxxxxx.redis.rds.aliyuncs.com:6379"},
        Password: "testaccount:Rp829dlwa",  // account:password format
    })

    // Set operation
    err := rdb.Set(ctx, "foo", "bar", 0).Err()
    if err != nil {
        panic(err)
    }

    // Get operation
    val, err := rdb.Get(ctx, "foo").Result()
    if err != nil {
        panic(err)
    }
    fmt.Println("foo =", val)
}
```

**redis-cli:**

```shell
# Must add -c parameter for cluster connection
./redis-cli -h r-bp1zxszhcgatnx****.redis.rds.aliyuncs.com -p 6379 -c

# Verify password
AUTH testaccount:Rp829dlwa
```

**Reference:** [Use direct connection mode to connect to cluster instance](https://help.aliyun.com/en/redis/user-guide/use-a-private-endpoint-to-connect-to-an-apsaradb-for-redis-instance)
