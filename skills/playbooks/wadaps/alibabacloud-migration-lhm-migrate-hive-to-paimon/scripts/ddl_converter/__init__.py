"""Hive DDL to DLF DDL converter - standalone sub-package.

This package provides a lightweight, standalone CLI for converting Hive DDL
to DLF (Data Lake Formation) DDL. Supports two output modes:
- Paimon inner tables (USING paimon)
- FORMAT external tables (USING ORC/CSV/PARQUET + OPTIONS path)

Usage:
  cat hive_ddl.sql | python scripts/ddl_converter/cli.py --mode paimon
  cat hive_ddl.sql | python scripts/ddl_converter/cli.py --mode ext \\
    --source-hdfs-nameservice ns1 --oss-bucket bucket --oss-prefix prefix
  cat hive_ddl.sql | python scripts/ddl_converter/cli.py --mode both \\
    --source-hdfs-nameservice ns1 --oss-bucket bucket --oss-prefix prefix
"""
