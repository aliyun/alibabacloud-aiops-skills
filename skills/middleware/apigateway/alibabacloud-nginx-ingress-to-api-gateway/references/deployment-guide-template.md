# 迁移报告模板

迁移报告 Step 5 输出模板。agent 根据实际迁移结果填充具体值。

## 6.1 前置检查

- 确认 IngressClass `apig` 存在：`kubectl get ingressclass apig`
- 确认 APIG 网关可达
- 降低 DNS TTL

## 6.2 迁移操作

根据兼容性分析结果，选择对应的迁移路径：

### 场景一：完全兼容（无不兼容注解）

所有注解均为兼容或可忽略类型，无需额外插件开发。请直接参考阿里云官方文档完成迁移：

> 📖 [Nginx Ingress 迁移到云原生 API 网关](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway)

按照文档步骤操作即可。

### 场景二：不完全兼容（存在不兼容注解）

按以下顺序操作：

**第一步：构建并推送自定义 WasmPlugin 镜像**

```bash
# 登录镜像仓库
docker login <your-registry>
# 为每个自定义插件打标签并推送
docker tag higress-wasm-<name>:v1 <your-registry>/higress-wasm-<name>:v1
docker push <your-registry>/higress-wasm-<name>:v1
```

**第二步：将 Ingress YAML 中的 OCI URL 占位符替换为真实的 WasmPlugin 镜像地址**

```bash
# 替换自定义插件 OCI 占位符
sed -i 's|<YOUR_REGISTRY>|your-actual-registry.com/namespace|g' all-migrated-ingress.yaml
# 替换内置插件区域占位符（如需要）
sed -i 's|<REGION>|cn-hangzhou|g' all-migrated-ingress.yaml
```

**第三步：将替换后的 Ingress YAML 部署到集群中**

```bash
kubectl apply -f all-migrated-ingress.yaml
kubectl get ingress -l migration.higress.io/source=nginx
```

**第四步：参考官方文档继续后续操作**

> 📖 [Nginx Ingress 迁移到云原生 API 网关](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway)

在文档步骤一「指定 IngressClass」处，需要将 IngressClass 指定为 `apig`。

> ⚠️ **网关版本要求**：使用 WasmPlugin 需确保云原生 API 网关版本在 **2.1.16 及以上**。如果当前网关版本低于 2.1.16，需要先升级网关版本或创建新网关后再进行迁移。

## 6.3 验证路由

- 阶段一：路由可达性 — 验证网关能正确接收和转发流量
- 阶段二：WasmPlugin 功能验证 — 针对每种插件类型提供具体的 curl 命令：
  - 认证插件：无凭证时预期 401/403，有效凭证时预期 200
  - 响应头插件：检查注入的 header 是否存在
  - WAF 插件：发送攻击载荷，预期 403
需根据用户 Ingress 中的实际域名和路径定制 curl 命令。

## 6.4 流量切换

DNS/SLB 切换表（域名 → 网关地址），所有测试通过后再执行。

## 6.5 迁移后监控（48 小时以上）

- APIG 控制台检查
- 5xx 错误监控
- WasmPlugin 健康状态
- DNS TTL 恢复
- nginx 缩容时间线

## 6.6 回滚

```bash
kubectl delete ingress -l migration.higress.io/source=nginx
# 将 DNS 恢复指向原 nginx-ingress
```
