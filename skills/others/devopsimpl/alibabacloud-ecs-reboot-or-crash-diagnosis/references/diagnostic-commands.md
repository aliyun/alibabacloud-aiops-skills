# Diagnostic Commands Reference

本文档提供诊断检查项和命令参考。**Agent 应根据实际操作系统类型和版本，动态生成适配的诊断命令。**

> **重要原则**：
> - 不同 Linux 发行版的服务名称、日志路径、工具命令可能不同
> - 先通过 `DescribeInstances` 获取 OSType 和 OSName，再生成适配的命令
> - 命令应包含错误处理，避免因路径不存在或命令不可用而中断

---

## Linux 系统诊断

### 检查项清单

| 检查项 | 目的 | 参考命令 |
|--------|------|----------|
| 系统重启记录 | 查看历史重启时间和来源 | `last reboot`, `who -b` |
| 系统日志中的重启/关机记录 | 识别正常/异常关机 | `grep -i "reboot\|shutdown" /var/log/messages` 或 `/var/log/syslog` |
| Kernel Panic 记录 | 检测内核崩溃 | `dmesg | grep -i panic`, 日志文件搜索 |
| OOM Killer 记录 | 检测内存不足导致的进程终止 | 日志文件搜索 "Out of memory", "oom", "Kill process" |
| OOM Panic 配置 | 判断 OOM 是否会触发系统重启 | `sysctl -n vm.panic_on_oom` |
| Kdump 服务状态 | 验证崩溃转储是否配置并启用 | `systemctl status kdump` 或 `systemctl status kdump-tools` |
| Kdump 配置文件 | 获取转储文件存储路径 | `/etc/kdump.conf` 或 `/etc/default/kdump-tools` |
| 崩溃转储文件 | 检查是否存在 vmcore/dump 文件 | 检查配置的路径或默认 `/var/crash` |

### 操作系统差异对照表

| 项目 | RHEL/CentOS/Alibaba Cloud Linux | Ubuntu/Debian |
|------|--------------------------------|---------------|
| 系统日志路径 | `/var/log/messages` | `/var/log/syslog` |
| Kdump 服务名 | `kdump` | `kdump-tools` |
| Kdump 配置文件 | `/etc/kdump.conf` | `/etc/default/kdump-tools` |
| 崩溃转储文件名 | `vmcore` (目录: `127.0.0.1-date-time/`) | `dump.*` + `dmesg.*` |
| 默认转储路径 | `/var/crash` | `/var/crash` |

### 命令示例参考

以下命令仅供参考，Agent 应根据实际操作系统动态调整。

#### 1. 获取系统信息

```bash
# 操作系统版本
cat /etc/os-release

# 内核版本
uname -r

# 系统运行时间
uptime
```

#### 2. 系统重启历史

```bash
# 重启历史记录
last reboot | head -10

# 最近一次启动时间
who -b
```

#### 3. 系统日志检查

**RHEL/CentOS/Alibaba Cloud Linux:**
```bash
# 重启/关机相关日志
grep -i "reboot\|shutdown\|restart" /var/log/messages | tail -20

# Kernel Panic 记录
dmesg | grep -i "panic\|oops" | tail -20
grep -i "kernel panic" /var/log/messages | tail -10

# OOM 记录
grep -i "out of memory\|oom\|kill process" /var/log/messages | tail -20
```

**Ubuntu/Debian:**
```bash
# 重启/关机相关日志
grep -i "reboot\|shutdown\|restart" /var/log/syslog | tail -20

# Kernel Panic 记录
dmesg | grep -i "panic\|oops" | tail -20
grep -i "kernel panic" /var/log/syslog | tail -10

# OOM 记录
grep -i "out of memory\|oom\|kill process" /var/log/syslog | tail -20
```

#### 4. OOM Panic 配置

```bash
# 检查 OOM 时是否触发 panic
sysctl -n vm.panic_on_oom

# 返回值说明:
# 0 - OOM 只杀死进程，系统继续运行
# 1 - OOM 触发 kernel panic，导致系统重启
```

#### 5. Kdump 状态检查

**RHEL/CentOS/Alibaba Cloud Linux:**
```bash
# 检查 kdump 服务状态
systemctl status kdump

# 检查是否已配置
cat /etc/kdump.conf

# 获取转储路径 (默认 /var/crash)
grep "^path" /etc/kdump.conf
```

**Ubuntu/Debian:**
```bash
# 检查 kdump-tools 服务状态
systemctl status kdump-tools

# 检查是否已配置
cat /etc/default/kdump-tools

# 检查内核 crashkernel 参数
cat /proc/cmdline | grep crashkernel
```

#### 6. 崩溃转储文件检查

```bash
# 检查转储目录
ls -la /var/crash/

# RHEL/CentOS: 查找 vmcore 文件
find /var/crash -name "vmcore*" -type f -exec ls -lh {} \;

# Ubuntu/Debian: 查找 dump 和 dmesg 文件
find /var/crash -name "dump.*" -type f -exec ls -lh {} \;
find /var/crash -name "dmesg.*" -type f -exec ls -lh {} \;

# 检查最近 7 天的转储文件
find /var/crash -type f \( -name "vmcore*" -o -name "dump.*" -o -name "dmesg.*" \) -mtime -7
```

---

## Kdump 配置建议

### 何时需要建议配置 Kdump

以下情况应建议用户配置 Kdump：

1. **检测到 Kernel Panic 迹象但无 vmcore 文件**
   - dmesg 或系统日志中有 panic 记录
   - 但 `/var/crash` 目录为空或不存在

2. **Kdump 服务未运行**
   - `systemctl status kdump` 显示 inactive/failed
   - `systemctl status kdump-tools` 显示 inactive/failed

3. **内核未配置 crashkernel 参数**
   - `/proc/cmdline` 中没有 `crashkernel=` 参数

### Kdump 配置参考

**RHEL/CentOS/Alibaba Cloud Linux:**

```bash
# 1. 安装 kexec-tools (如未安装)
yum install -y kexec-tools

# 2. 配置 /etc/kdump.conf
# 默认配置通常可用，关键配置项：
# path /var/crash          # 转储文件存储路径
# core_collector makedumpfile -l --message-level 1 -d 31  # 压缩转储

# 3. 在 /etc/default/grub 的 GRUB_CMDLINE_LINUX 中添加 crashkernel 参数
# crashkernel=auto  或  crashkernel=128M

# 4. 更新 grub 配置
grub2-mkconfig -o /boot/grub2/grub.cfg

# 5. 重启系统使 crashkernel 生效
reboot

# 6. 启用并启动 kdump 服务
systemctl enable kdump
systemctl start kdump
systemctl status kdump
```

**Ubuntu/Debian:**

```bash
# 1. 安装 kdump-tools
apt-get install -y kdump-tools

# 2. 配置 /etc/default/kdump-tools
# USE_KDUMP=1

# 3. 更新 grub 配置 (安装时通常会自动添加 crashkernel 参数)
update-grub

# 4. 重启系统
reboot

# 5. 验证服务状态
systemctl status kdump-tools
```

### Kdump 配置验证

```bash
# 验证 crashkernel 参数已生效
cat /proc/cmdline | grep crashkernel

# 验证 kdump 服务状态
systemctl status kdump  # RHEL/CentOS
systemctl status kdump-tools  # Ubuntu/Debian
```

---

## Windows 系统诊断

### 检查项清单

| 检查项 | 目的 | 参考 PowerShell 命令 |
|--------|------|----------------------|
| 系统信息 | 获取 Windows 版本和主机名 | `Get-ComputerInfo` |
| 系统运行时间 | 判断最近是否重启过 | `[WMI]'\\.\root\cimv2:Win32_OperatingSystem'` |
| 意外关机事件 | 检测非正常关机 | Event ID 41, 6008, 6006, 1074 |
| 内存转储配置 | 验证是否配置了崩溃转储 | 注册表 `CrashControl` |
| 页面文件配置 | 转储文件需要页面文件支持 | `Get-CimInstance Win32_PageFileUsage` |
| MEMORY.DMP 文件 | 检查完整内存转储文件 | `Test-Path C:\Windows\MEMORY.DMP` |
| Minidump 文件 | 检查小型转储文件 | `Get-ChildItem C:\Windows\Minidump` |
| BSOD 事件 | 检测蓝屏错误报告 | WER 事件日志 |

### 事件 ID 说明

| Event ID | 来源 | 含义 |
|----------|------|------|
| 41 | Kernel-Power | 系统意外重启（未正常关机） |
| 1074 | User32 | 正常关机/重启，记录原因 |
| 6008 | EventLog | 上次关机是意外的 |
| 6006 | EventLog | 事件日志服务已停止（正常关机） |

### 内存转储类型

| CrashDumpEnabled | 类型 | 说明 |
|------------------|------|------|
| 0 | None | 禁用内存转储 |
| 1 | Complete | 完整内存转储（最大，约等于内存大小） |
| 2 | Kernel | 内核内存转储（中等大小） |
| 3 | Small | 小内存转储（64KB，Minidump） |
| 7 | Automatic | 自动内存转储（推荐） |

### PowerShell 命令示例

```powershell
# 系统信息
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsArchitecture, CsName

# 系统运行时间
$os = Get-CimInstance Win32_OperatingSystem
$uptime = (Get-Date) - $os.LastBootUpTime
Write-Host "Last boot: $($os.LastBootUpTime)"
Write-Host "Uptime: $($uptime.Days) days, $($uptime.Hours) hours"

# 意外关机事件
Get-WinEvent -FilterHashtable @{LogName="System"; ID=41,1074,6008,6006} -ErrorAction SilentlyContinue | 
    Select-Object TimeCreated, Id, Message -First 10

# 内存转储配置
$crashControl = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl"
Write-Host "CrashDumpEnabled: $($crashControl.CrashDumpEnabled)"
Write-Host "DumpFile: $($crashControl.DumpFile)"
Write-Host "MinidumpDir: $($crashControl.MinidumpDir)"

# 页面文件配置
Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage

# 检查 MEMORY.DMP
$dumpFile = $crashControl.DumpFile
if (-not $dumpFile) { $dumpFile = "C:\Windows\MEMORY.DMP" }
if (Test-Path $dumpFile) {
    $fileInfo = Get-Item $dumpFile
    Write-Host "MEMORY.DMP found: Size=$([math]::Round($fileInfo.Length/1GB,2)) GB, Modified=$($fileInfo.LastWriteTime)"
}

# 检查 Minidump 文件
$minidumpDir = $crashControl.MinidumpDir
if (-not $minidumpDir) { $minidumpDir = "C:\Windows\Minidump" }
if (Test-Path $minidumpDir) {
    Get-ChildItem -Path $minidumpDir -Filter "*.dmp" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
}

# BSOD 事件
Get-WinEvent -FilterHashtable @{LogName="System"; ProviderName="Microsoft-Windows-WER-SystemErrorReporting"} -ErrorAction SilentlyContinue | 
    Select-Object TimeCreated, Id, Message -First 10
```

### Windows 内存转储配置建议

当检测到 BSOD 事件但无转储文件时，建议配置内存转储：

1. **通过系统属性配置**：
   - 右键"此电脑" → 属性 → 高级系统设置
   - 启动和故障恢复 → 设置
   - 选择"自动内存转储"或"内核内存转储"
   - 确保页面文件大小足够（至少内存大小 + 1MB）

2. **PowerShell 配置**：
```powershell
# 设置自动内存转储
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl" -Name "CrashDumpEnabled" -Value 7

# 确保页面文件存在且大小足够
# 通常由系统自动管理，检查方法：
$cs = Get-CimInstance Win32_ComputerSystem
if ($cs.AutomaticManagedPagefile) {
    Write-Host "Pagefile is automatically managed"
} else {
    # 手动配置页面文件
    # 需要重启生效
}
```

---

## 崩溃转储文件分析

### Linux vmcore 分析

如果找到 vmcore 文件，可读取 `vmcore-dmesg.txt` 进行初步分析：

```bash
# 查看 vmcore-dmesg.txt 内容
cat /var/crash/127.0.0.1-*/vmcore-dmesg.txt

# 关键信息搜索
grep -i "kernel panic" /var/crash/*/vmcore-dmesg.txt
grep -i "RIP:" /var/crash/*/vmcore-dmesg.txt
grep -i "Call Trace" /var/crash/*/vmcore-dmesg.txt
```

**关键信息解读**：

| 关键字 | 含义 |
|--------|------|
| `Kernel panic - not syncing: VFS` | 文件系统相关问题 |
| `Kernel panic - not syncing: Attempted to kill init` | init 进程崩溃 |
| `Kernel panic - not syncing: Out of memory` | OOM 导致崩溃 |
| `RIP: 0010:` | 崩溃时的指令位置 |
| `Call Trace:` | 调用栈 |
| `MCE` / `Machine Check Exception` | 硬件错误 |

> **注意**：深度 vmcore 分析需要使用 `crash` 工具和调试符号包，建议联系阿里云技术支持获取专业分析。

### Windows 转储文件分析

使用 WinDbg 或 BlueScreenView 工具分析：

```
# WinDbg 命令
!analyze -v          # 自动分析崩溃原因
k                    # 查看调用栈
.bugcheck            # 查看 bugcheck 代码
```

> **注意**：深度 dump 分析建议联系阿里云技术支持。

---

## 通过云助手执行命令

诊断命令通过阿里云云助手远程执行：

### Linux 命令执行

```bash
aliyun ecs run-command \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --type RunShellScript \
  --instance-id <INSTANCE_ID> \
  --timeout 3600 \
  --command-content '<SCRIPT_CONTENT>'
```

### Windows 命令执行

```bash
aliyun ecs run-command \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --type RunPowerShellScript \
  --instance-id <INSTANCE_ID> \
  --timeout 3600 \
  --command-content '<SCRIPT_CONTENT>'
```

### 获取命令执行结果

```bash
aliyun ecs describe-invocations \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID> \
  --invoke-id <INVOKE_ID>
```

**注意**：`Output` 字段为 Base64 编码，需要解码后查看。
