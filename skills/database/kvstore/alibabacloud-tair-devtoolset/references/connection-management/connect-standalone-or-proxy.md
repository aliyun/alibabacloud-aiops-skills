
## Connect Standalone or Proxy

Connect to Tair standard architecture or cluster/proxy mode instances using Redis-compatible clients.

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
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

public class JedisExample {
    public static void main(String[] args) {
        JedisPoolConfig config = new JedisPoolConfig();
        // The maximum number of idle connections
        config.setMaxIdle(200);
        // The maximum number of connections
        config.setMaxTotal(300);
        config.setTestOnBorrow(false);
        config.setTestOnReturn(false);
        // Replace the values of the host and password parameters with the endpoint and password of the instance
        String host = "r-bp1s1bt2tlq3p1****pd.redis.rds.aliyuncs.com";
        // For a default account, enter the password directly
        // For a newly created account, the password must be in the Account:Password format
        String password = "r-bp1s1bt2tlq3p1****:Database123";
        JedisPool pool = new JedisPool(config, host, 6379, 3000, password);
        Jedis jedis = null;
        try {
            jedis = pool.getResource();
            // Perform operations
            jedis.set("foo10", "bar");
            System.out.println(jedis.get("foo10"));
            jedis.zadd("sose", 0, "car");
            jedis.zadd("sose", 0, "bike");
            System.out.println(jedis.zrange("sose", 0, -1));
        } catch (Exception e) {
            // Handle a timeout or other exceptions
            e.printStackTrace();
        } finally {
            if (jedis != null) {
                jedis.close();
            }
        }
        // When the application exits, call this method to release resources
        pool.destroy();
    }
}
```

**redis-py (Python):**

```python
#!/usr/bin/env python
#-*- coding: utf-8 -*-
# pip install redis
import redis

# Replace the values of the host and port parameters with the endpoint and port of the instance
host = 'r-bp10noxlhcoim2****.redis.rds.aliyuncs.com'
port = 6379
# Replace the value of the pwd parameter with the password of the instance
# For a default account, you can directly enter the password
# For a newly created account, the password must be in the Account:Password format
pwd = 'testaccount:Rp829dlwa'
r = redis.Redis(host=host, port=port, password=pwd)
# After the connection is established, you can perform database operations
r.set('foo', 'bar')
print(r.get('foo'))
```

**PhpRedis (PHP):**

```php
// Install: pecl install redis
<?php
/* Replace the values of the host and port parameters with the endpoint and port of the instance */
$host = "r-bp10noxlhcoim2****.redis.rds.aliyuncs.com";
$port = 6379;
/* Replace the values of the user and pwd parameters with the account and password of the instance */
$user = "testaccount";
$pwd = "Rp829dlwa";
$redis = new Redis();
if ($redis->connect($host, $port) == false) {
    die($redis->getLastError());
}
if ($redis->auth([$user, $pwd]) == false) {
    die($redis->getLastError());
}
/* After the authentication is complete, you can perform database operations */
if ($redis->set("foo", "bar") == false) {
    die($redis->getLastError());
}
$value = $redis->get("foo");
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
        <!-- Use Lettuce 6.3.0+ to prevent blackhole issues -->
        <dependency>
            <groupId>io.lettuce</groupId>
            <artifactId>lettuce-core</artifactId>
            <version>6.3.0.RELEASE</version>
        </dependency>
    </dependencies>
</project>
```

```java
// Spring Data Redis With Jedis
@Configuration
public class RedisConfig {
    @Bean
    JedisConnectionFactory redisConnectionFactory() {
        // Connection address (hostName) and port obtained from instance details page
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration(
            "r-8vbwds91ie1rdl****.redis.zhangbei.rds.aliyuncs.com", 6379);
        // Password format: account:password
        config.setPassword(RedisPassword.of("testaccount:Rp829dlwa"));
        
        JedisPoolConfig jedisPoolConfig = new JedisPoolConfig();
        // Max connections, cannot exceed instance limit
        jedisPoolConfig.setMaxTotal(30);
        // Max idle connections
        jedisPoolConfig.setMaxIdle(20);
        // Disable testOnBorrow/Return to avoid extra PING
        jedisPoolConfig.setTestOnBorrow(false);
        jedisPoolConfig.setTestOnReturn(false);
        
        JedisClientConfiguration jedisClientConfiguration = JedisClientConfiguration.builder()
            .usePooling().poolConfig(jedisPoolConfig).build();
        
        return new JedisConnectionFactory(config, jedisClientConfiguration);
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

**node-redis (Node.js):**

```javascript
// npm install redis
const redis = require('redis');

const client = redis.createClient({
    socket: {
        host: 'r-bp10noxlhcoim2****.redis.rds.aliyuncs.com',
        port: 6379
    },
    // For default account, enter password directly
    // For custom account, use 'account:password' format
    password: 'testaccount:Rp829dlwa'
});

client.on('error', (err) => console.log('Redis Client Error', err));

async function main() {
    await client.connect();
    await client.set('foo', 'bar');
    const value = await client.get('foo');
    console.log(value);
    await client.disconnect();
}

main();
```

**ioredis (Node.js):**

```javascript
// npm install ioredis
const Redis = require('ioredis');

const redis = new Redis({
    host: 'r-bp10noxlhcoim2****.redis.rds.aliyuncs.com',
    port: 6379,
    // For default account, enter password directly
    // For custom account, use 'account:password' format
    password: 'testaccount:Rp829dlwa',
    db: 0
});

redis.set('foo', 'bar', (err, result) => {
    if (err) {
        console.error(err);
        return;
    }
    console.log('Set result:', result);
});

redis.get('foo', (err, result) => {
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
    
    rdb := redis.NewClient(&redis.Options{
        Addr:     "r-bp10noxlhcoim2****.redis.rds.aliyuncs.com:6379",
        // For default account, enter password directly
        // For custom account, use 'account:password' format
        Password: "testaccount:Rp829dlwa",
        DB:       0,
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

**Reference:** [Connect to Tair using a client](https://www.alibabacloud.com/help/en/redis/user-guide/use-a-client-to-connect-to-an-apsaradb-for-redis-instance)
