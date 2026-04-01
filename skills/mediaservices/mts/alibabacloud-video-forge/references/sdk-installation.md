# SDK 安装指南

## 依赖检查

本 Skill 的脚本需要以下 Python 包：
- `alibabacloud-mts20140618` - MPS SDK
- `alibabacloud-credentials` - 凭证管理 SDK
- `oss2` - OSS SDK

## 推荐的安装方法

### 方法 1：虚拟环境（推荐）

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖（带超时处理）
pip install --timeout 1200 alibabacloud-mts20140618 alibabacloud-credentials oss2

# 验证安装
python -c "import alibabacloud_mts20140618; print('MPS SDK OK')"
python -c "import oss2; print('OSS SDK OK')"
```

### 方法 2：用户安装（权限不足时）

```bash
pip install --user --timeout 1200 alibabacloud-mts20140618 alibabacloud-credentials oss2
```

### 方法 3：使用镜像源（网络较慢时）

```bash
# 清华镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    alibabacloud-mts20140618 alibabacloud-credentials oss2

# 阿里云镜像源
pip install -i https://mirrors.aliyun.com/pypi/simple \
    alibabacloud-mts20140618 alibabacloud-credentials oss2
```

## 故障排除

详见 [troubleshooting.md](troubleshooting.md)。

### 快速参考

```bash
# 检查 Python 版本
python3 --version

# 检查 Aliyun CLI 版本
aliyun version

# 验证环境变量
python3 scripts/load_env.py --check-only

# 测试 SDK
python -c "import alibabacloud_mts20140618; print('MPS SDK OK')"
python -c "import oss2; print('OSS SDK OK')"
```

### 常见问题

**安装超时：**
```bash
# 增加超时时间重试
pip install --timeout 1800 --retries 3 alibabacloud-mts20140618 alibabacloud-credentials oss2
```

**权限拒绝：**
```bash
# 使用用户安装
pip install --user alibabacloud-mts20140618 alibabacloud-credentials oss2

# 或修复权限
sudo chown -R $(whoami) ~/.local/lib/python*/site-packages
```

**网络问题：**
```bash
# 使用备用索引 URL
pip install --index-url https://pypi.org/simple/ \
    --trusted-host pypi.org --trusted-host pypi.python.org \
    alibabacloud-mts20140618 alibabacloud-credentials oss2
```

**验证安装：**
```bash
# 检查所有必需的包是否已安装
python -c "
try:
    import alibabacloud_mts20140618
    import alibabacloud_credentials  
    import oss2
    print('All dependencies installed successfully!')
except ImportError as e:
    print(f'Missing dependency: {e}')
"
```

## 性能优化建议

1. **使用虚拟环境** - 避免依赖冲突
2. **启用凭证缓存** - 生产环境中提高性能
3. **选择合适的预设** - 根据视频需求选择
4. **监控任务状态** - 使用合理的轮询间隔（建议 30-60 秒）
5. **批量操作** - 减少 API 调用次数

## 支持资源

- **官方文档**: [阿里云 MPS 文档](https://help.aliyun.com/document_detail/29220.html)
- **API 参考**: [MPS API Explorer](https://api.aliyun.com/product/Mts)
- **社区支持**: [阿里云开发者论坛](https://developer.aliyun.com/)
- **问题跟踪**: 向项目维护者报告 bug
