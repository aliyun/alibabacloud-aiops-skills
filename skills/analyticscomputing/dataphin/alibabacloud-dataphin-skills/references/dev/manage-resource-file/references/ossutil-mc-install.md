# 对象存储上传工具安装指南（ossutil / minio mc）

> 本 skill 根据 `get-file-storage-credential` 返回的 `StorageType` 选择上传工具：
> - **oss** → ossutil（v1，支持 `--sts-token`）
> - **ceph** → minio mc
>
> 上传时通过**命令行 flag 传凭证**，因此安装后**无需执行 `ossutil config` / `mc alias set` 的持久化配置**（ceph 上传前需临时 `mc alias set`，见 SKILL §8 步骤 2b）。

---

## 一、ossutil（StorageType=oss 时使用）

> 使用 ossutil **v1**（`ossutil cp ... --sts-token`），非 ossutil 2.0（2.0 命令语法不同）。
> 官方文档：[下载并安装命令行工具 ossutil](https://help.aliyun.com/zh/oss/developer-reference/install-ossutil)

### 1. macOS（Intel / Apple Silicon 通用）

官方一键脚本，自动识别架构并安装到 `/usr/local/bin`：

```bash
sudo -v ; curl https://gosspublic.alicdn.com/ossutil/install.sh | sudo bash
```

> 依赖 `unzip` 或 `7z` 解压；macOS 自带 `unzip`，一般无需额外安装。

验证：

```bash
ossutil version
# 或直接执行查看支持的命令
ossutil
```

### 2. Linux

#### 2a. 一键脚本（x86_64 / ARM64 自动识别，安装到 `/usr/bin`）

```bash
sudo -v ; curl https://gosspublic.alicdn.com/ossutil/install.sh | sudo bash
```

> 需 `unzip` 或 `7z`：`sudo yum install -y unzip` 或 `sudo apt-get install -y unzip`。

#### 2b. 手动下载二进制（无 sudo / 离线环境）

```bash
# x86_64
curl -o /usr/local/bin/ossutil https://gosspublic.alicdn.com/ossutil/1.7.19/ossutil64
# ARM64（如 alinux ARM / 鲲鹏）
curl -o /usr/local/bin/ossutil https://gosspublic.alicdn.com/ossutil/1.7.19/ossutilarm64

chmod +x /usr/local/bin/ossutil
ossutil version
```

> 版本号 `1.7.19` 为当前稳定版，可按官方文档替换为最新版。

### 3. Windows

1. 下载 Windows x86-64 安装包：[官方下载页](https://help.aliyun.com/zh/oss/developer-reference/install-ossutil)（"Windows x86 64bit"链接）。
2. 解压到任意目录（如 `C:\ossutil`）。
3. 进入解压目录，双击 `ossutil.bat` 或在 cmd / PowerShell 中运行。

验证（PowerShell / cmd）：

```powershell
.\ossutil.exe version
```

> Windows 下本 skill 上传命令需用 `ossutil.exe`，参数同 Linux/macOS。

---

## 二、minio mc（StorageType=ceph 时使用）

> 官方下载页（国内可访问）：https://www.minio.org.cn/download.shtml（按 macOS / Linux / Windows 切换 Tab）
> 文档：[MinIO Client 文档（国内镜像）](https://docs.minio.org.cn/docs/minio/linux/reference/minio-mc.html)
> 二进制下载目录（国内镜像）：https://dl.minio.org.cn/client/mc/release/

### 1. macOS

#### 方式 A：Homebrew（推荐，需可访问 GitHub）

```bash
brew install minio/stable/mc
# 或
brew install minio-mc
```

> 若 Homebrew 拉取缓慢/失败，改用下面的「方式 B 手动下载二进制」。

验证：

```bash
mc --version
```

#### 方式 B：手动下载二进制（国内推荐，镜像可直连）

```bash
# Apple Silicon (arm64)
curl -o /usr/local/bin/mc https://dl.minio.org.cn/client/mc/release/darwin-arm64/mc
# Intel (amd64)
curl -o /usr/local/bin/mc https://dl.minio.org.cn/client/mc/release/darwin-amd64/mc

chmod +x /usr/local/bin/mc
mc --version
```

> 也可在 https://www.minio.org.cn/download.shtml#/macos 页面直接下载对应架构的二进制。

### 2. Linux

#### 2a. x86_64（最常见）

```bash
wget https://dl.minio.org.cn/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
mc --version
```

#### 2b. ARM64（如 alinux ARM / 鲲鹏 / AWS Graviton）

```bash
wget https://dl.minio.org.cn/client/mc/release/linux-arm64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
mc --version
```

#### 2c. 其他架构

| 架构 | 下载地址 |
|------|---------|
| 64-bit PPC | `https://dl.minio.org.cn/client/mc/release/linux-ppc64le/mc` |
| s390x | `https://dl.minio.org.cn/client/mc/release/linux-s390x/mc` |

> Linux 也可在 https://www.minio.org.cn/download.shtml#/linux 页面下载。

### 3. Windows

下载 `mc.exe`：

```powershell
curl -o mc.exe https://dl.minio.org.cn/client/mc/release/windows-amd64/mc.exe
.\mc.exe --version
```

> 也可在 https://www.minio.org.cn/download.shtml#/windows 页面下载。
> 建议放入 PATH 目录（如 `C:\Windows` 或自定义目录并加入系统 PATH）。

---

## 三、安装后验证清单

| 工具 | 验证命令 | 预期输出 |
|------|---------|---------|
| ossutil | `ossutil version` 或 `ossutil` | 输出版本号 / 支持的命令列表 |
| mc | `mc --version` | 输出 `mc version RELEASE....` |

### 排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `ossutil: command not found` | 未安装或不在 PATH | 重新执行安装脚本，或确认 `/usr/bin` / `/usr/local/bin` 在 `PATH` 中 |
| `mc: command not found` | 未安装或不在 PATH | `brew install minio-mc` 或将二进制 `mv` 到 `/usr/local/bin` |
| Linux 安装脚本报缺 `unzip` | 未装解压工具 | `yum install -y unzip` / `apt-get install -y unzip` |
| macOS `sudo curl ... \| sudo bash` 失败 | 权限或网络 | 用 `brew install` 方式，或手动下载二进制到 `/usr/local/bin` |
| 国内访问 `dl.min.io` 超时 | min.io 国际域名不可达 | 改用国内镜像 `dl.minio.org.cn`（见本文 §二） |
| Windows `ossutil.exe` 无法运行 | 被 SmartScreen 拦截 | 右键属性 → 勾选"解除锁定"后重试 |
