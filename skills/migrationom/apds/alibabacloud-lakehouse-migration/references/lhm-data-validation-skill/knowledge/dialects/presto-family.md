# Presto 方言族（衍生）

包含：Amazon Athena

继承 PrestoDialect，基准方言详见 `presto.md`。

## Amazon Athena

### 共性（继承自 Presto）

- **NULL 处理**: `COALESCE(CAST(col AS VARCHAR), 'default')`
- **ARRAY 索引**: 1-based
- **CRC32**: ❌ 不支持
- **MD5**: `lower(to_hex(md5(to_utf8(col))))` ✅
- **LENGTH**: `length(col)` ✅ 字符数
- **BOOLEAN**: `true` / `false`

### 特殊行为

无额外差异，完全继承 Presto 行为。

### 已知陷阱

共享 Presto 的所有已知陷阱（ARRAY 1-based、MD5 格式复杂、无 CRC32）。
