# Tracepoint Usage

This document describes the steps for using perf-tools tpoint to capture kernel tracepoint events.

## Usage Steps

1. Download and extract perf-tools:
   ```bash
   wget --connect-timeout=5 --timeout=30 --tries=2 -O perf-tools-1.0.tar.gz 'https://github.com/brendangregg/perf-tools/archive/refs/tags/v1.0.tar.gz' && tar -zxvf perf-tools-1.0.tar.gz
   ```
2. Capture the specified tracepoint:
   ```bash
   ./perf-tools-1.0/bin/tpoint -H {tracepoint}
   ```
