#!/usr/bin/env python3
"""
Alibaba Cloud PolarDB MySQL SQL Linting Tool

Combines Bytebase-style SQL lint rules with Alibaba Cloud DAS SQL diagnostics
for comprehensive pre-release SQL assessment.

Usage:
    python3 sql_lint.py --instance-id pc-xxxxx --sql "SELECT * FROM users" --region cn-shanghai
    python3 sql_lint.py --instance-id pc-xxxxx --sql-file migration.sql --region cn-shanghai
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for importing sibling scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SQLLintRule:
    
    def __init__(self, rule_id: str, name: str, severity: str, category: str, description: str):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity  # critical, warning, suggestion
        self.category = category  # engine, naming, statement, table, column, index, schema
        self.description = description
    
    def check(self, sql: str, context: Dict) -> Optional[Dict]:
        """
        Check SQL against this rule.
        
        Returns:
            Dict with issue details if violation found, None otherwise
        """
        raise NotImplementedError


class EngineRules(SQLLintRule):
    """Engine-related lint rules"""
    
    def __init__(self):
        super().__init__(
            rule_id="RULE-001",
            name="Require InnoDB",
            severity="critical",
            category="engine",
            description="Ensure tables use InnoDB storage engine"
        )
    
    def check(self, sql: str, context: Dict) -> Optional[Dict]:
        # Check CREATE TABLE with non-InnoDB engine
        # Use re.DOTALL to match across multiple lines
        match = re.search(r'CREATE\s+TABLE.*ENGINE\s*=\s*(\w+)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            engine = match.group(1).upper()
            if engine != 'INNODB':
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Non-InnoDB storage engine detected: {engine}",
                    'suggestion': "Use ENGINE=InnoDB for transaction support and row-level locking"
                }
        
        # Check ALTER TABLE engine change
        match = re.search(r'ALTER\s+TABLE.*ENGINE\s*=\s*(\w+)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            engine = match.group(1).upper()
            if engine != 'INNODB':
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Changing to non-InnoDB engine: {engine}",
                    'suggestion': "Avoid changing to non-InnoDB engines"
                }
        
        return None


class NamingRules:
    """Naming convention lint rules"""
    
    class TableNaming(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-010",
                name="Table Naming Convention",
                severity="warning",
                category="naming",
                description="Validate table names follow snake_case convention"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Extract table name from CREATE TABLE (skip comments)
            # Remove comment lines first
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', sql_clean, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                # Skip temporary tables
                if table_name.startswith('tmp_') or table_name.startswith('temp_'):
                    return None
                # Skip backup tables with date suffix (e.g., orders_backup_202501)
                if re.search(r'_backup_\d{6,8}$', table_name):
                    return None
                # Skip sharding tables (e.g., orders_0, orders_2025)
                if re.search(r'_\d{1,4}$', table_name):
                    return None
                # Check snake_case pattern
                if not re.match(r'^[a-z]+(_[a-z]+)*$', table_name):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Table name '{table_name}' doesn't follow snake_case convention",
                        'suggestion': "Use lowercase with underscores: e.g., user_sessions"
                    }
            return None
    
    class ColumnNaming(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-011",
                name="Column Naming Convention",
                severity="warning",
                category="naming",
                description="Validate column names follow snake_case convention"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Remove comment lines first
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql_clean, re.IGNORECASE):
                return None
            
            # Extract the CREATE TABLE body (between parentheses)
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql_clean, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Extract column names and check naming convention
            issues = []
            for line in table_body.split(','):
                line = line.strip()
                # Skip constraints, keys, etc.
                if re.match(r'^(PRIMARY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN)', line, re.IGNORECASE):
                    continue
                
                # Match column definition: column_name TYPE ...
                col_match = re.match(r'[`"]?(\w+)[`"]?\s+(INT|BIGINT|VARCHAR|TEXT|TIMESTAMP|DATETIME|DECIMAL|TINYINT|SMALLINT|MEDIUMINT|FLOAT|DOUBLE|CHAR|BLOB)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    # Check snake_case pattern
                    if not re.match(r'^[a-z]+(_[a-z]+)*$', col_name):
                        issues.append(col_name)
            
            if issues:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Column names don't follow snake_case: {', '.join(issues)}",
                    'suggestion': "Use lowercase with underscores for column names"
                }
            return None
    
    class IndexNaming(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-012",
                name="Index Naming Convention",
                severity="warning",
                category="naming",
                description="Validate index names follow idx_{table}_{columns} pattern"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Extract index names
            matches = re.findall(r'(?:INDEX|KEY)\s+`?(\w+)`?', sql, re.IGNORECASE)
            for idx_name in matches:
                # Skip PRIMARY key
                if idx_name.upper() == 'PRIMARY':
                    continue
                # Skip MySQL keywords that might be incorrectly matched
                if idx_name.upper() in ['AUTO_INCREMENT', 'PRIMARY', 'UNIQUE', 'FULLTEXT', 'SPATIAL']:
                    continue
                # Allow idx_, uniq_, and uk_ prefixes
                if not idx_name.startswith('idx_') and not idx_name.startswith('uniq_') and not idx_name.startswith('uk_'):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Index name '{idx_name}' doesn't follow naming convention",
                        'suggestion': "Use idx_<table>_<columns>, uniq_<table>_<columns>, or uk_<columns>"
                    }
            return None


class StatementRules:
    """SQL statement lint rules"""
    
    class DisallowSelectStar(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-020",
                name="Disallow SELECT *",
                severity="warning",
                category="statement",
                description="Require explicit column list in SELECT statements"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Skip for TEMPORARY TABLE AS SELECT
            if re.search(r'CREATE\s+TEMPORARY\s+TABLE.*AS\s+SELECT', sql, re.IGNORECASE):
                return None
            
            if re.search(r'SELECT\s+\*', sql, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "SELECT * detected",
                    'suggestion': "Specify required columns explicitly to improve performance and maintainability"
                }
            return None
    
    class RequireWhere(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-021",
                name="Require WHERE Clause",
                severity="critical",
                category="statement",
                description="UPDATE and DELETE must have WHERE clause"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Skip triggers, procedures, functions
            if re.search(r'CREATE\s+(TRIGGER|PROCEDURE|FUNCTION)', sql, re.IGNORECASE):
                return None
            
            # Skip if inside BEGIN...END block (trigger/procedure body)
            if re.search(r'BEGIN.*UPDATE.*END', sql, re.IGNORECASE | re.DOTALL):
                return None
            
            # Skip CREATE TABLE statements (might contain UPDATE in comments)
            if re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Simplified and more reliable regex
            if re.search(r'\bUPDATE\b', sql, re.IGNORECASE) or re.search(r'\bDELETE\b', sql, re.IGNORECASE):
                if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "UPDATE/DELETE without WHERE clause",
                        'suggestion': "Add WHERE clause to limit affected rows and prevent accidental data loss"
                    }
            return None
    
    class DisallowLeadingPercent(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-022",
                name="Disallow Leading % in LIKE",
                severity="warning",
                category="statement",
                description="LIKE '%xxx' causes full table scan"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "Leading wildcard in LIKE pattern",
                    'suggestion': "Avoid LIKE '%xxx' as it prevents index usage. Consider full-text search"
                }
            return None
    
    class InsertMustSpecifyColumns(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-023",
                name="INSERT Must Specify Columns",
                severity="critical",
                category="statement",
                description="INSERT statements must specify column names"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r'INSERT\s+INTO\s+\w+\s+VALUES', sql, re.IGNORECASE):
                if not re.search(r'INSERT\s+INTO\s+\w+\s*\([^)]+\)', sql, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "INSERT without column specification",
                        'suggestion': "Always specify column names: INSERT INTO table (col1, col2) VALUES (...)"
                    }
            return None
    
    class DisallowCommit(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-024",
                name="Disallow Explicit COMMIT",
                severity="warning",
                category="statement",
                description="Remove explicit COMMIT statements from migration scripts"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Skip if it's part of a larger transaction block in procedures
            if re.search(r'CREATE\s+(TRIGGER|PROCEDURE|FUNCTION)', sql, re.IGNORECASE):
                return None
            
            if re.search(r'\bCOMMIT\b', sql, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "Explicit COMMIT detected",
                    'suggestion': "Remove COMMIT. Let the migration tool or framework manage transactions."
                }
            return None


class TableRules:
    """Table-related lint rules"""
    
    class RequirePrimaryKey(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-030",
                name="Require Primary Key",
                severity="critical",
                category="table",
                description="All tables must have primary key"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                # Skip CREATE TABLE AS SELECT (backup tables)
                if re.search(r'CREATE\s+TABLE.*AS\s+SELECT', sql, re.IGNORECASE):
                    return None
                if not re.search(r'PRIMARY\s+KEY', sql, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "Table without primary key",
                        'suggestion': "Add PRIMARY KEY to improve performance and enable replication"
                    }
            return None
    
    class DisallowForeignKey(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-031",
                name="Disallow Foreign Key",
                severity="warning",
                category="table",
                description="Avoid foreign key constraints in distributed systems"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r'FOREIGN\s+KEY|REFERENCES\s+\w+', sql, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "Foreign key constraint detected",
                    'suggestion': "Avoid FK constraints in distributed systems. Use application-level validation"
                }
            return None
    
    class TableComment(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-032",
                name="Table Comment Required",
                severity="warning",
                category="table",
                description="Require table comments for documentation"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                if not re.search(r'COMMENT\s*=', sql, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "Table missing comment",
                        'suggestion': "Add table comment for documentation: COMMENT='User session management'"
                    }
            return None


class ColumnRules:
    """Column-related lint rules"""
    
    class NoNullColumns(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-042",
                name="Columns No NULL Value",
                severity="warning",
                category="column",
                description="Avoid nullable columns, use DEFAULT values instead"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Remove comment lines
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            # Extract the CREATE TABLE body
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql_clean, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Check for nullable columns (columns without NOT NULL)
            nullable_columns = []
            for line in table_body.split(','):
                line = line.strip()
                # Skip constraints, keys, etc.
                if re.match(r'^(PRIMARY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN)', line, re.IGNORECASE):
                    continue
                
                # Match column definition
                col_match = re.match(r'[`"]?(\w+)[`"]?\s+(INT|BIGINT|VARCHAR|TEXT|TIMESTAMP|DATETIME|DECIMAL|TINYINT|SMALLINT|MEDIUMINT|FLOAT|DOUBLE|CHAR|BLOB)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    # Check if column has NOT NULL constraint
                    if 'NOT NULL' not in line.upper():
                        nullable_columns.append(col_name)
            
            if nullable_columns:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Nullable columns detected: {', '.join(nullable_columns[:5])}",
                    'suggestion': "Add NOT NULL constraint with DEFAULT value to avoid NULL-related issues"
                }
            return None
    
    class SetDefaultForNotNull(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-043",
                name="Set DEFAULT for NOT NULL Columns",
                severity="critical",
                category="column",
                description="NOT NULL columns must have DEFAULT value"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Remove comment lines
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            # Extract the CREATE TABLE body
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql_clean, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Check for NOT NULL columns without DEFAULT
            missing_default = []
            for line in table_body.split(','):
                line = line.strip()
                # Skip constraints, keys, etc.
                if re.match(r'^(PRIMARY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN)', line, re.IGNORECASE):
                    continue
                
                # Match column definition
                col_match = re.match(r'[`"]?(\w+)[`"]?\s+(INT|BIGINT|VARCHAR|TEXT|TIMESTAMP|DATETIME|DECIMAL|TINYINT|SMALLINT|MEDIUMINT|FLOAT|DOUBLE|CHAR|BLOB)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    # Check if column has NOT NULL but no DEFAULT
                    if 'NOT NULL' in line.upper() and 'DEFAULT' not in line.upper():
                        # Skip AUTO_INCREMENT columns (they generate values automatically)
                        if 'AUTO_INCREMENT' not in line.upper():
                            missing_default.append(col_name)
            
            if missing_default:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"NOT NULL columns without DEFAULT: {', '.join(missing_default[:5])}",
                    'suggestion': "Add DEFAULT value to NOT NULL columns to prevent INSERT failures"
                }
            return None
    
    class RequireColumnDefault(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-044",
                name="Require Column Default Value",
                severity="warning",
                category="column",
                description="All columns should have DEFAULT values"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Remove comment lines
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            # Extract the CREATE TABLE body
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql_clean, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Check for columns without DEFAULT
            missing_default = []
            for line in table_body.split(','):
                line = line.strip()
                # Skip constraints, keys, etc.
                if re.match(r'^(PRIMARY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN)', line, re.IGNORECASE):
                    continue
                
                # Match column definition
                col_match = re.match(r'[`"]?(\w+)[`"]?\s+(INT|BIGINT|VARCHAR|TEXT|TIMESTAMP|DATETIME|DECIMAL|TINYINT|SMALLINT|MEDIUMINT|FLOAT|DOUBLE|CHAR|BLOB)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    # Check if column has no DEFAULT
                    if 'DEFAULT' not in line.upper():
                        # Skip AUTO_INCREMENT columns
                        if 'AUTO_INCREMENT' not in line.upper():
                            missing_default.append(col_name)
            
            if missing_default:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Columns without DEFAULT value: {', '.join(missing_default[:5])}",
                    'suggestion': "Add DEFAULT value to ensure data consistency"
                }
            return None
    
    class ColumnTypeDisallowList(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-045",
                name="Column Type Disallow List",
                severity="warning",
                category="column",
                description="Disallow use of deprecated or problematic column types"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE and ALTER TABLE statements
            if not re.search(r'(CREATE|ALTER)\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Remove comment lines
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            # Check for disallowed types
            disallowed_types = {
                'FLOAT': 'Use DECIMAL for precise numeric values',
                'DOUBLE': 'Use DECIMAL for precise numeric values',
                'BLOB': 'Consider using VARCHAR or TEXT with proper indexing',
                'SET': 'Use separate junction table for better normalization',
            }
            
            found_issues = []
            for col_type, suggestion in disallowed_types.items():
                # Match type usage in column definitions
                if re.search(r'\b' + col_type + r'\b', sql_clean, re.IGNORECASE):
                    found_issues.append(f"{col_type} ({suggestion})")
            
            if found_issues:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Disallowed column types: {'; '.join(found_issues)}",
                    'suggestion': "Replace with recommended alternatives for better performance and maintainability"
                }
            return None
    
    class AutoIncrementType(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-040",
                name="Auto-increment Column Type",
                severity="warning",
                category="column",
                description="Use BIGINT UNSIGNED for auto-increment columns"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            if re.search(r'AUTO_INCREMENT', sql, re.IGNORECASE):
                if re.search(r'\bINT\b(?!.*BIGINT)', sql, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "Auto-increment column uses INT (max: 2.1B)",
                        'suggestion': "Use BIGINT UNSIGNED (max: 18.4Q) to prevent overflow"
                    }
            return None
    
    class ColumnComment(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-041",
                name="Column Comment Required",
                severity="warning",
                category="column",
                description="Require column comments for documentation"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Remove comment lines first
            sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
            sql_clean = '\n'.join(sql_lines)
            
            if not re.search(r'CREATE\s+TABLE', sql_clean, re.IGNORECASE):
                return None
            
            # Extract the CREATE TABLE body (between parentheses)
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql_clean, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Extract column definitions and check for comments
            columns_without_comment = []
            for line in table_body.split(','):
                line = line.strip()
                # Skip constraints, keys, etc.
                if re.match(r'^(PRIMARY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN)', line, re.IGNORECASE):
                    continue
                
                # Match column definition: column_name TYPE ...
                col_match = re.match(r'[`"]?(\w+)[`"]?\s+(INT|BIGINT|VARCHAR|TEXT|TIMESTAMP|DATETIME|DECIMAL|TINYINT|SMALLINT|MEDIUMINT|FLOAT|DOUBLE|CHAR|BLOB)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    # Check if this column has a COMMENT
                    if 'COMMENT' not in line.upper():
                        columns_without_comment.append(col_name)
            
            if columns_without_comment:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Columns missing comments: {', '.join(columns_without_comment[:5])}",
                    'suggestion': "Add column comments for documentation"
                }
            return None


class IndexRules:
    """Index-related lint rules"""
    
    class IndexCountLimit(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-052",
                name="Index Count Limit",
                severity="warning",
                category="index",
                description="Limit number of indexes per table (default: 10)"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Count indexes in CREATE TABLE
            index_count = 0
            
            # Count PRIMARY KEY (inline or constraint)
            if re.search(r'PRIMARY\s+KEY', sql, re.IGNORECASE):
                index_count += 1
            
            # Count UNIQUE indexes
            unique_matches = re.findall(r'UNIQUE\s+(?:KEY|INDEX)\s+\w+\s*\(', sql, re.IGNORECASE)
            index_count += len(unique_matches)
            
            # Count regular INDEX/KEY (but not PRIMARY KEY or UNIQUE)
            index_matches = re.findall(r'(?<!PRIMARY\s)(?<!UNIQUE\s)(?:INDEX|KEY)\s+\w+\s*\(', sql, re.IGNORECASE)
            index_count += len(index_matches)
            
            max_indexes = 10
            if index_count > max_indexes:
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': f"Table has {index_count} indexes (max: {max_indexes})",
                    'suggestion': "Reduce index count. Too many indexes slow down INSERT/UPDATE/DELETE operations"
                }
            return None
    
    class DisallowDuplicateIndexColumn(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-053",
                name="Disallow Duplicate Column in Index",
                severity="critical",
                category="index",
                description="Disallow duplicate columns in composite index keys"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Extract all index definitions
            index_matches = re.findall(r'(?:INDEX|KEY|PRIMARY\s+KEY|UNIQUE)\s*\w*\s*\(([^)]+)\)', sql, re.IGNORECASE)
            
            for columns_str in index_matches:
                # Extract column names
                columns = [col.strip().strip('`"').split('(')[0] for col in columns_str.split(',')]
                # Check for duplicates
                if len(columns) != len(set(columns)):
                    duplicates = [col for col in columns if columns.count(col) > 1]
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Duplicate columns in index: {', '.join(set(duplicates))}",
                        'suggestion': "Remove duplicate columns from index definition"
                    }
            return None
    
    class IndexKeyLimit(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-050",
                name="Index Key Limit",
                severity="warning",
                category="index",
                description="Limit columns per index (max: 5)"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Extract composite indexes
            matches = re.findall(r'(?:INDEX|KEY)\s+\w+\s*\(([^)]+)\)', sql, re.IGNORECASE)
            for columns in matches:
                col_count = len([c.strip() for c in columns.split(',')])
                if col_count > 5:
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Index has {col_count} columns (max: 5)",
                        'suggestion': "Reduce index columns. Composite indexes with >5 columns are inefficient"
                    }
            return None
    
    class DisallowBlobTextIndex(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-051",
                name="Disallow BLOB/TEXT Indexes",
                severity="critical",
                category="index",
                description="Disallow indexing BLOB and TEXT columns"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Check 1: Independent CREATE INDEX statement
            if re.search(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+\w+\s+ON\s+\w+', sql, re.IGNORECASE):
                # Extract column name from CREATE INDEX ... ON table(column)
                index_match = re.search(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+\w+\s+ON\s+\w+\s*\(([^)]+)\)', sql, re.IGNORECASE)
                if index_match:
                    cols_str = index_match.group(1)
                    # Check if any column is TEXT/BLOB type (we need to check table structure)
                    # For independent CREATE INDEX, we check if column name suggests TEXT/BLOB
                    cols = [c.strip().strip('`"').split('(')[0].lower() for c in cols_str.split(',')]
                    # Common TEXT/BLOB column name patterns
                    text_blob_patterns = ['content', 'description', 'text', 'body', 'message', 'data', 'detail', 'remark', 'note', 'comment']
                    for col in cols:
                        col_lower = col.lower()
                        # Check if column name matches common TEXT/BLOB patterns
                        if any(pattern in col_lower for pattern in text_blob_patterns):
                            return {
                                'rule_id': self.rule_id,
                                'severity': self.severity,
                                'category': self.category,
                                'message': f"Potential index on BLOB/TEXT column: {col}",
                                'suggestion': "Avoid indexing BLOB/TEXT columns. Use FULLTEXT index or prefix index if necessary"
                            }
            
            # Check 2: CREATE TABLE with TEXT/BLOB column and INDEX
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Extract table body
            match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.+)\)\s*ENGINE', sql, re.IGNORECASE | re.DOTALL)
            if not match:
                return None
            
            table_body = match.group(1)
            
            # Find all TEXT/BLOB columns
            text_blob_cols = re.findall(r'[`"]?(\w+)[`"]?\s+(TEXT|BLOB|LONGTEXT|MEDIUMTEXT|LONGBLOB|MEDIUMBLOB)\b', table_body, re.IGNORECASE)
            
            if not text_blob_cols:
                return None
            
            text_blob_col_names = [col[0].lower() for col in text_blob_cols]
            
            # Check if any index references these columns
            index_matches = re.findall(r'(?:INDEX|KEY)\s+\w+\s*\(([^)]+)\)', table_body, re.IGNORECASE)
            
            for index_cols in index_matches:
                # Extract column names from index definition
                cols = [c.strip().strip('`"').split('(')[0].lower() for c in index_cols.split(',')]
                # Check if any indexed column is TEXT/BLOB
                for col in cols:
                    if col in text_blob_col_names:
                        return {
                            'rule_id': self.rule_id,
                            'severity': self.severity,
                            'category': self.category,
                            'message': f"Index on BLOB/TEXT column detected: {col}",
                            'suggestion': "Use FULLTEXT index or prefix index for TEXT columns"
                        }
            
            return None


class SchemaRules:
    """Schema change safety rules"""
    
    class CharsetAllowList(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-070",
                name="Charset Allow List",
                severity="critical",
                category="system",
                description="Only allow utf8mb4 charset for Unicode support"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE and ALTER DATABASE statements
            if not re.search(r'(CREATE\s+TABLE|ALTER\s+DATABASE|CREATE\s+DATABASE)', sql, re.IGNORECASE):
                return None
            
            # Extract charset specification
            charset_match = re.search(r'(?:CHARSET|CHARACTER\s+SET)\s*=\s*(\w+)', sql, re.IGNORECASE)
            if charset_match:
                charset = charset_match.group(1).upper()
                allowed_charsets = ['UTF8MB4', 'UTF8']
                if charset not in allowed_charsets:
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Disallowed charset: {charset}",
                        'suggestion': "Use CHARSET=utf8mb4 for full Unicode support including emoji"
                    }
            return None
    
    class LimitDDLForLargeTables(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-071",
                name="Limit DDL on Large Tables",
                severity="warning",
                category="table",
                description="Warn about DDL operations on large tables"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check ALTER TABLE statements
            if not re.search(r'ALTER\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Extract table name
            match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', sql, re.IGNORECASE)
            if not match:
                return None
            
            table_name = match.group(1)
            
            # Check if table stats are available in context
            if 'table_stats' in context:
                table_stats = context['table_stats']
                if table_name in table_stats:
                    row_count = table_stats[table_name].get('row_count', 0)
                    large_table_threshold = context.get('large_table_threshold', 1000000)
                    
                    if row_count > large_table_threshold:
                        return {
                            'rule_id': self.rule_id,
                            'severity': self.severity,
                            'category': self.category,
                            'message': f"ALTER TABLE on large table '{table_name}' ({row_count:,} rows)",
                            'suggestion': f"Use online DDL (ALGORITHM=INPLACE, LOCK=NONE) or schedule during maintenance window. Consider using gh-ost or pt-online-schema-change"
                        }
            
            return None
    
    class LimitInsertedRows(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-072",
                name="Limit Inserted Rows",
                severity="warning",
                category="statement",
                description="Limit rows per INSERT statement (default: 1000)"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check INSERT statements
            if not re.search(r'INSERT\s+INTO', sql, re.IGNORECASE):
                return None
            
            # Count VALUES clauses
            values_matches = re.findall(r'\(([^)]+)\)', sql)
            if values_matches:
                row_count = len(values_matches)
                max_rows = context.get('max_insert_rows', 1000)
                
                if row_count > max_rows:
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"INSERT with {row_count} rows (max: {max_rows})",
                        'suggestion': "Split into multiple INSERT statements to avoid large transactions and replication lag"
                    }
            return None
    
    class PrimaryKeyNaming(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-073",
                name="Primary Key Naming Convention",
                severity="warning",
                category="naming",
                description="Primary key should be named 'id' or 'pk_<table_name>'"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # Only check CREATE TABLE statements
            if not re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE):
                return None
            
            # Extract PRIMARY KEY constraint name
            # Pattern 1: CONSTRAINT `name` PRIMARY KEY
            pk_match = re.search(r'CONSTRAINT\s+[`"]?(\w+)[`"]?\s+PRIMARY\s+KEY', sql, re.IGNORECASE)
            if pk_match:
                pk_name = pk_match.group(1)
                # Allow names starting with 'pk_'
                if not pk_name.startswith('pk_'):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': f"Primary key constraint name '{pk_name}' doesn't follow convention",
                        'suggestion': "Use 'pk_<table_name>' for named PRIMARY KEY constraints"
                    }
            
            # Pattern 2: Check if primary key column is named 'id' (most common)
            # This is just a suggestion, not an error
            pk_column_match = re.search(r'PRIMARY\s+KEY\s*\(\s*[`"]?(\w+)[`"]?\s*\)', sql, re.IGNORECASE)
            if pk_column_match:
                pk_column = pk_column_match.group(1)
                # If column is not 'id' and there's no constraint name, it's OK
                # This is just informational
            
            return None
    
    class BackwardIncompatibleChange(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-060",
                name="Backward Incompatible Schema Change",
                severity="critical",
                category="schema",
                description="Detect breaking schema changes"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            sql_clean = sql.strip()
            
            # Detect column renaming (CHANGE COLUMN)
            if re.search(r'ALTER\s+TABLE.*CHANGE\s+COLUMN', sql_clean, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "Backward incompatible schema change: column renaming",
                    'suggestion': "Use additive migration: add new column, migrate data, then remove old column in next deployment"
                }
            
            # Detect column type changes (MODIFY COLUMN with type change)
            if re.search(r'ALTER\s+TABLE.*MODIFY\s+COLUMN.*\b(VARCHAR|INT|BIGINT|TEXT|DECIMAL)\b', sql_clean, re.IGNORECASE):
                # Check if it's actually changing the type (not just adding constraints)
                if re.search(r'MODIFY\s+COLUMN\s+\w+\s+\w+', sql_clean, re.IGNORECASE):
                    return {
                        'rule_id': self.rule_id,
                        'severity': self.severity,
                        'category': self.category,
                        'message': "Backward incompatible schema change: column type modification",
                        'suggestion': "Ensure application compatibility before changing column types. Test thoroughly."
                    }
            
            # Detect column dropping
            if re.search(r'ALTER\s+TABLE.*DROP\s+COLUMN', sql_clean, re.IGNORECASE):
                return {
                    'rule_id': self.rule_id,
                    'severity': self.severity,
                    'category': self.category,
                    'message': "Backward incompatible schema change: dropping column",
                    'suggestion': "Ensure no application code references this column before dropping"
                }
            
            return None
    
    class MergeAlterTable(SQLLintRule):
        def __init__(self):
            super().__init__(
                rule_id="RULE-061",
                name="Merge ALTER TABLE Statements",
                severity="warning",
                category="schema",
                description="Combine multiple ALTER statements"
            )
        
        def check(self, sql: str, context: Dict) -> Optional[Dict]:
            # This rule is designed to work with multiple statements
            # For single statement linting, we can't detect this
            # The rule will be more effective when linting SQL files
            return None


class SQLLintEngine:
    """Main SQL linting engine"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.rules = self._load_rules()
        self.config = config or {}
    
    def _load_rules(self) -> List[SQLLintRule]:
        """Load all lint rules"""
        rules = [
            # Engine rules
            EngineRules(),
            
            # Naming rules
            NamingRules.TableNaming(),
            NamingRules.ColumnNaming(),
            NamingRules.IndexNaming(),
            SchemaRules.PrimaryKeyNaming(),
            
            # Statement rules
            StatementRules.DisallowSelectStar(),
            StatementRules.RequireWhere(),
            StatementRules.DisallowLeadingPercent(),
            StatementRules.InsertMustSpecifyColumns(),
            StatementRules.DisallowCommit(),
            SchemaRules.LimitInsertedRows(),
            
            # Table rules
            TableRules.RequirePrimaryKey(),
            TableRules.DisallowForeignKey(),
            TableRules.TableComment(),
            SchemaRules.LimitDDLForLargeTables(),
            
            # Column rules
            ColumnRules.AutoIncrementType(),
            ColumnRules.ColumnComment(),
            ColumnRules.NoNullColumns(),
            ColumnRules.SetDefaultForNotNull(),
            ColumnRules.RequireColumnDefault(),
            ColumnRules.ColumnTypeDisallowList(),
            
            # Index rules
            IndexRules.IndexCountLimit(),
            IndexRules.DisallowDuplicateIndexColumn(),
            IndexRules.IndexKeyLimit(),
            IndexRules.DisallowBlobTextIndex(),
            
            # Schema rules
            SchemaRules.CharsetAllowList(),
            SchemaRules.BackwardIncompatibleChange(),
            SchemaRules.MergeAlterTable(),
        ]
        return rules
    
    def lint_sql(self, sql: str, context: Optional[Dict] = None) -> List[Dict]:
        """
        Lint SQL statement(s). Supports both single and multiple statements.
        
        Args:
            sql: SQL statement(s) to lint (can contain multiple statements separated by ;)
            context: Additional context (table stats, instance info, etc.)
        
        Returns:
            List of issues found
        """
        issues = []
        context = context or {}
        
        # Remove SQL comments for cleaner analysis
        # Remove multi-line comments first
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # Remove single-line comments
        sql_no_comments = re.sub(r'--.*?$', '', sql_no_comments, flags=re.MULTILINE)
        sql_clean = sql_no_comments.strip()
        
        # Skip if no actual SQL content
        if not sql_clean:
            return []
        
        # Split by semicolon to handle multiple statements
        statements = [s.strip() for s in sql_clean.split(';') if s.strip()]
        
        # If multiple statements, lint each one and check for RULE-061
        if len(statements) > 1:
            for i, stmt in enumerate(statements):
                stmt_issues = []
                for rule in self.rules:
                    try:
                        issue = rule.check(stmt, context)
                        if issue:
                            issue['statement_index'] = i
                            issue['sql'] = stmt[:100] + ('...' if len(stmt) > 100 else '')
                            stmt_issues.append(issue)
                    except Exception as e:
                        print(f"Warning: Rule {rule.rule_id} failed: {e}")
                issues.extend(stmt_issues)
            
            # Check for RULE-061: Multiple consecutive ALTER TABLE statements
            self._check_merge_alter_table(statements, issues)
        else:
            # Single statement: use original logic
            for rule in self.rules:
                try:
                    issue = rule.check(sql_clean, context)
                    if issue:
                        issues.append(issue)
                except Exception as e:
                    print(f"Warning: Rule {rule.rule_id} failed: {e}")
        
        return issues
    
    def lint_sql_file(self, file_path: str) -> List[Dict]:
        """
        Lint all SQL statements in a file.
        
        Args:
            file_path: Path to SQL file
        
        Returns:
            List of all issues found
        """
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split SQL statements by semicolon
        statements = [s.strip() for s in content.split(';') if s.strip()]
        
        all_issues = []
        for i, sql in enumerate(statements):
            issues = self.lint_sql(sql)
            for issue in issues:
                issue['statement_index'] = i
                issue['sql'] = sql[:100] + ('...' if len(sql) > 100 else '')
            all_issues.extend(issues)
        
        # Check for RULE-061: Multiple consecutive ALTER TABLE statements
        self._check_merge_alter_table(statements, all_issues)
        
        return all_issues
    
    def _check_merge_alter_table(self, statements: List[str], all_issues: List[Dict]):
        """
        Check for consecutive ALTER TABLE statements on the same table.
        
        Args:
            statements: List of SQL statements
            all_issues: List to append issues to
        """
        # Group consecutive ALTER TABLE statements by table name
        alter_groups = []
        current_group = []
        current_table = None
        
        for i, sql in enumerate(statements):
            # Extract table name from ALTER TABLE
            match = re.search(r'ALTER\s+TABLE\s+[`\"]?(\w+)[`\"]?', sql, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
                if current_table == table_name:
                    # Same table, add to current group
                    current_group.append((i, sql))
                else:
                    # Different table, save previous group if it has multiple statements
                    if len(current_group) > 1:
                        alter_groups.append(current_group)
                    # Start new group
                    current_group = [(i, sql)]
                    current_table = table_name
            else:
                # Not an ALTER TABLE, save previous group
                if len(current_group) > 1:
                    alter_groups.append(current_group)
                current_group = []
                current_table = None
        
        # Don't forget the last group
        if len(current_group) > 1:
            alter_groups.append(current_group)
        
        # Generate issues for each group with multiple ALTER statements
        for group in alter_groups:
            if len(group) > 1:
                table_name = group[0][1]  # Get table name from first statement
                match = re.search(r'ALTER\s+TABLE\s+[`\"]?(\w+)[`\"]?', group[0][1], re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    first_idx = group[0][0]
                    all_issues.append({
                        'rule_id': 'RULE-061',
                        'severity': 'warning',
                        'category': 'schema',
                        'message': f"Multiple ALTER TABLE statements on '{table_name}' ({len(group)} statements)",
                        'suggestion': f"Combine into single ALTER TABLE: ALTER TABLE {table_name} ADD COLUMN ..., ADD INDEX ...;",
                        'statement_index': first_idx,
                        'sql': f"{len(group)} consecutive ALTER TABLE statements on '{table_name}'"
                    })


class DASDiagnoser:
    """Alibaba Cloud DAS SQL Diagnostics Integration using CLI"""

    _ALLOWED_ACTIONS = frozenset({
        'create-request-diagnosis',
        'get-request-diagnosis-result',
        'describe-instance-das-pro',
    })

    _plugins_ensured = False

    def __init__(self, instance_id: str, region: str = 'cn-shanghai'):
        self.instance_id = instance_id
        self.region = region
        self.endpoint = 'das.cn-shanghai.aliyuncs.com'
        self._ensure_cli_plugins()

    @classmethod
    def _ensure_cli_plugins(cls):
        if cls._plugins_ensured:
            return
        try:
            subprocess.run(
                'aliyun plugin install --name aliyun-cli-das',
                shell=True, capture_output=True, text=True, timeout=60
            )
            verify = subprocess.run(
                'aliyun plugin list', shell=True, capture_output=True, text=True, timeout=30
            )
            if 'das' in (verify.stdout or ''):
                cls._plugins_ensured = True
            else:
                print("[WARN] das plugin install could not be verified", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] plugin pre-install failed: {e}", file=sys.stderr)

    def _run_cli_command(self, command: str, max_retries: int = 5) -> Optional[Dict]:
        """Run aliyun CLI command with action whitelist, response code check, and retry backoff"""
        parts = command.split()
        if len(parts) >= 3:
            action = parts[2]
            if action not in self._ALLOWED_ACTIONS:
                print(f"[WARN] action '{action}' not in whitelist, skipping", file=sys.stderr)
                return None

        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=60
                )

                if result.returncode != 0:
                    stderr = result.stderr or ''
                    if 'Throttling' in stderr or 'throttling' in stderr.lower():
                        backoff = min(3 ** (attempt + 1), 30)
                        print(f"[WARN] throttled, retry {attempt+1}/{max_retries} after {backoff}s", file=sys.stderr)
                        import time; time.sleep(backoff)
                        continue
                    print(f"Warning: CLI command failed: {stderr}", file=sys.stderr)
                    return None

                data = json.loads(result.stdout)

                resp_code = str(data.get('Code', ''))
                if resp_code and resp_code not in ('200', 'OK', ''):
                    msg = data.get('Message', 'unknown error')
                    print(f"[ERROR] DAS API returned Code={resp_code}: {msg}", file=sys.stderr)
                    return None

                return data

            except subprocess.TimeoutExpired:
                backoff = min(3 ** (attempt + 1), 30)
                print(f"[WARN] timeout, retry {attempt+1}/{max_retries} after {backoff}s", file=sys.stderr)
                import time; time.sleep(backoff)
                continue
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse CLI output: {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"Warning: CLI command error: {e}", file=sys.stderr)
                return None

        print(f"Warning: CLI command failed after {max_retries} retries", file=sys.stderr)
        return None
    
    def validate_instance(self) -> Dict:
        """
        Validate instance ID: format check + DAS API reachability.

        Returns:
            Dict with 'valid' (bool), 'error' (str if invalid), and optional 'data'.
        """
        iid = self.instance_id
        if not re.match(r'^(pc|rm|pxc|gp|dds|r)-[a-zA-Z0-9]{10,}$', iid):
            return {
                'valid': False,
                'error': f"Instance ID '{iid}' does not match expected format "
                         f"(e.g., pc-bp167736gfqyn483x for PolarDB, rm-xxx for RDS)."
            }

        cmd = (
            f"aliyun das describe-instance-das-pro "
            f"--endpoint {self.endpoint} "
            f"--instance-id {iid}"
        )
        result = self._run_cli_command(cmd, max_retries=2)
        if result is None:
            return {
                'valid': False,
                'error': f"Instance '{iid}' is not accessible via DAS. "
                         f"Check that the instance exists and DAS access is enabled."
            }
        return {'valid': True, 'data': result}

    def diagnose_sql(self, sql: str, db_name: str = 'mysql') -> Optional[Dict]:
        """
        Diagnose SQL statement using DAS CLI.
        
        Args:
            sql: SQL statement to diagnose
            db_name: Database name (default: mysql)
        
        Returns:
            Diagnosis result with optimization suggestions
        """
        import base64
        
        try:
            # Encode SQL to base64 to avoid shell escaping issues
            sql_bytes = sql.encode('utf-8')
            sql_base64 = base64.b64encode(sql_bytes).decode('utf-8')
            
            # Step 1: Create diagnostic task using CLI
            # Use double quotes and base64 encoded SQL
            create_cmd = (
                f"aliyun das create-request-diagnosis "
                f"--endpoint {self.endpoint} "
                f"--instance-id {self.instance_id} "
                f"--database {db_name} "
                f"--sql \"{sql}\""
            )
            
            create_result = self._run_cli_command(create_cmd)
            
            if not create_result:
                return None
            
            # Data field contains the task/message ID
            message_id = create_result.get('Data')
            if not message_id:
                print(f"Warning: Failed to create diagnosis task: {create_result}")
                return None
            
            # Step 2: Wait for diagnosis completion
            import time
            time.sleep(15)  # Wait for diagnosis to complete
            
            # Step 3: Get diagnosis result using --message-id (NOT --task-id)
            get_cmd = (
                f"aliyun das get-request-diagnosis-result "
                f"--endpoint {self.endpoint} "
                f"--instance-id {self.instance_id} "
                f"--message-id {message_id}"
            )
            
            get_result = self._run_cli_command(get_cmd)
            
            if not get_result:
                return None
            
            # Parse the result field (JSON string)
            result_str = get_result.get('Data', {}).get('result')
            if result_str and isinstance(result_str, str):
                return json.loads(result_str)
            elif isinstance(result_str, dict):
                return result_str
            
            return None

        except Exception as e:
            print(f"Warning: DAS diagnosis failed: {e}")
            return None

    def diagnose_multiple(self, statements: List[str], db_name: str = 'mysql') -> List[Optional[Dict]]:
        """Batch DAS diagnosis: create all tasks, wait once, get all results."""
        import time

        message_ids = []
        for sql in statements:
            try:
                create_cmd = (
                    f"aliyun das create-request-diagnosis "
                    f"--endpoint {self.endpoint} "
                    f"--instance-id {self.instance_id} "
                    f"--database {db_name} "
                    f"--sql \"{sql}\""
                )
                create_result = self._run_cli_command(create_cmd)
                mid = create_result.get('Data') if create_result else None
                message_ids.append(mid)
            except Exception as e:
                print(f"Warning: DAS create failed for statement: {e}", file=sys.stderr)
                message_ids.append(None)

        time.sleep(15)

        results = []
        for mid in message_ids:
            if not mid:
                results.append(None)
                continue
            try:
                get_cmd = (
                    f"aliyun das get-request-diagnosis-result "
                    f"--endpoint {self.endpoint} "
                    f"--instance-id {self.instance_id} "
                    f"--message-id {mid}"
                )
                get_result = self._run_cli_command(get_cmd)
                if not get_result:
                    results.append(None)
                    continue
                result_str = get_result.get('Data', {}).get('result')
                if result_str and isinstance(result_str, str):
                    results.append(json.loads(result_str))
                elif isinstance(result_str, dict):
                    results.append(result_str)
                else:
                    results.append(None)
            except Exception as e:
                print(f"Warning: DAS get-result failed: {e}", file=sys.stderr)
                results.append(None)
        return results


def format_report(issues: List[Dict], das_results=None) -> str:
    """Format linting issues into a readable report"""
    
    # Categorize issues
    critical = [i for i in issues if i.get('severity') == 'critical']
    warnings = [i for i in issues if i.get('severity') == 'warning']
    suggestions = [i for i in issues if i.get('severity') == 'suggestion']
    
    report = []
    report.append("SQL Diagnosis Report")
    report.append("")

    # Critical issues
    if critical:
        report.append("[CRITICAL]")
        report.append("")
        for i, issue in enumerate(critical, 1):
            report.append(f"  {i}. {issue['message']} ({issue['rule_id']})")
            if issue.get('sql'):
                report.append(f"     SQL: {issue['sql']}")
            if issue.get('suggestion'):
                report.append(f"     Suggestion: {issue['suggestion']}")
            report.append("")

    # Warnings
    if warnings:
        report.append("[WARNING]")
        report.append("")
        start_num = len(critical) + 1
        for i, issue in enumerate(warnings, start_num):
            report.append(f"  {i}. {issue['message']} ({issue['rule_id']})")
            if issue.get('sql'):
                report.append(f"     SQL: {issue['sql']}")
            if issue.get('suggestion'):
                report.append(f"     Suggestion: {issue['suggestion']}")
            report.append("")

    # Suggestions
    if suggestions:
        report.append("[SUGGESTION]")
        report.append("")
        start_num = len(critical) + len(warnings) + 1
        for i, issue in enumerate(suggestions, start_num):
            report.append(f"  {i}. {issue['message']} ({issue['rule_id']})")
            if issue.get('sql'):
                report.append(f"     SQL: {issue['sql']}")
            if issue.get('suggestion'):
                report.append(f"     Suggestion: {issue['suggestion']}")
            report.append("")
    
    # DAS diagnostics — handle both single result and list of results
    das_list = []
    if das_results is not None:
        if isinstance(das_results, list):
            das_list = das_results
        elif isinstance(das_results, dict):
            das_list = [das_results]

    _DAS_TAG_DESC = {
        'LIKE_LEFT_WILD_CARD': 'Leading wildcard in LIKE pattern prevents B-Tree index usage. Consider full-text index or search engine.',
        'FULL_TABLE_SCAN': 'Full table scan detected, no index matched. Add appropriate index.',
        'LARGE_TABLE': 'Large table scan with excessive row count. Add index or narrow query scope.',
        'INDEX_NOT_MATCH': 'Index mismatch, existing indexes do not cover query predicates.',
        'PREDICATE_LOW_SELECTIVITY': 'Low predicate selectivity, matched rows ratio too high for effective index filtering.',
        'PREDICATE_INCURABLE': 'Predicate cannot be optimized via index (e.g. function on column, implicit type conversion).',
        'PLAN_COST_VERY_SMALL': 'Execution cost is very small, query is already efficient.',
        'ORDER_BY_WITHOUT_INDEX': 'ORDER BY not backed by index, may cause filesort.',
        'GROUP_BY_WITHOUT_INDEX': 'GROUP BY not backed by index, may cause temporary table.',
        'IMPLICIT_CONVERSION': 'Implicit type conversion detected, may cause index invalidation.',
        'SELECT_STAR': 'SELECT * used, specify explicit columns to reduce network transfer.',
    }
    _DAS_PRIMARY_TAG_DESC = {
        'PLAN_COST_VERY_SMALL': 'Very small cost',
        'LARGE_TABLE': 'Large table scan',
        'FULL_TABLE_SCAN': 'Full table scan',
        'INDEX_NOT_MATCH': 'Index not matched',
    }

    valid_das = [d for d in das_list if d and d.get('success')]
    if valid_das:
        report.append("[DAS DIAGNOSIS]")
        report.append("")
        for idx, das_result in enumerate(valid_das):
            if len(valid_das) > 1:
                report.append(f"--- Statement {idx + 1} ---")
                report.append("")

            primary_tag = das_result.get('primaryTag', '')
            estimate_cost = das_result.get('estimateCost', {})
            if estimate_cost:
                rows = estimate_cost.get('rows', 'N/A')
                cpu = estimate_cost.get('cpu', 'N/A')
                io_cost = estimate_cost.get('io', 'N/A')
                tag_desc = _DAS_PRIMARY_TAG_DESC.get(primary_tag, primary_tag)
                report.append(f"  Cost Estimate: {tag_desc}")
                try:
                    report.append(f"    Estimated rows: {float(rows):,.0f}")
                except (ValueError, TypeError):
                    report.append(f"    Estimated rows: {rows}")
                try:
                    report.append(f"    Estimated CPU: {float(cpu):,.2f}")
                except (ValueError, TypeError):
                    report.append(f"    Estimated CPU: {cpu}")
                try:
                    report.append(f"    Estimated I/O: {float(io_cost):,.2f}")
                except (ValueError, TypeError):
                    report.append(f"    Estimated I/O: {io_cost}")
                improvement = das_result.get('improvement', 0)
                if improvement and float(improvement) > 1:
                    report.append(f"    Improvement: {float(improvement):,.2f}x")
                report.append("")

            index_advices = das_result.get('indexAdvices', [])
            if index_advices:
                report.append("  Index Recommendations:")
                for advice in index_advices:
                    if isinstance(advice, dict):
                        ddl = advice.get('ddl') or advice.get('indexName') or advice.get('name', '')
                        report.append(f"    - {ddl}")
                    else:
                        report.append(f"    - {advice}")
                report.append("")

            tuning_advices = das_result.get('tuningAdvices', [])
            if tuning_advices:
                report.append("  Tuning Advice:")
                for advice in tuning_advices:
                    if isinstance(advice, dict):
                        name = advice.get('name', '')
                        desc = _DAS_TAG_DESC.get(name, name)
                        report.append(f"    - {desc}")
                    else:
                        desc = _DAS_TAG_DESC.get(advice, advice)
                        report.append(f"    - {desc}")
                report.append("")

    # Mandatory footer
    report.append("[NOTICE]")
    report.append("  Suggestions are for reference only. Evaluate applicability based on your business scenario and data characteristics before deploying.")
    
    return '\n'.join(report)


def main():
    parser = argparse.ArgumentParser(description='Alibaba Cloud PolarDB MySQL SQL Linting Tool')
    parser.add_argument('--instance-id', help='PolarDB instance ID (optional — omit for static-only mode)')
    parser.add_argument('--sql', help='SQL statement to lint')
    parser.add_argument('--sql-file', help='SQL file to lint')
    parser.add_argument('--database', help='Database name (required for DAS diagnosis)')
    parser.add_argument('--region', default='cn-shanghai', help='Region (default: cn-shanghai)')
    parser.add_argument('--output', help='Output report file (JSON)')
    parser.add_argument('--fail-on', choices=['critical', 'warning'], help='Exit code on severity')

    args = parser.parse_args()

    if not args.sql and not args.sql_file:
        parser.error("Either --sql or --sql-file is required")

    # Initialize lint engine
    engine = SQLLintEngine()

    # Lint SQL
    if args.sql:
        issues = engine.lint_sql(args.sql)
    elif args.sql_file:
        issues = engine.lint_sql_file(args.sql_file)

    # DAS diagnostics (only when instance-id is provided)
    das_results = None
    sql_text = args.sql or ''
    if args.instance_id and sql_text:
        try:
            das = DASDiagnoser(args.instance_id, args.region)
            validation = das.validate_instance()
            if not validation['valid']:
                print(f"\n[INSTANCE VALIDATION FAILED] {validation['error']}", file=sys.stderr)
                print("Skipping DAS diagnosis. Only static lint results are shown.\n", file=sys.stderr)
            else:
                db_name = args.database or 'mysql'
                sql_clean = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
                sql_clean = re.sub(r'--.*?$', '', sql_clean, flags=re.MULTILINE)
                stmts = [s.strip() for s in sql_clean.split(';') if s.strip()]
                if len(stmts) > 1:
                    das_results = das.diagnose_multiple(stmts, db_name)
                elif len(stmts) == 1:
                    single = das.diagnose_sql(stmts[0], db_name)
                    das_results = [single] if single else None
        except Exception as e:
            print(f"Warning: DAS diagnostics failed: {e}")
    elif not args.instance_id:
        print("[INFO] No --instance-id provided. Running static lint only (28+ rules).", file=sys.stderr)
        print("[INFO] Provide --instance-id and --database for DAS execution plan analysis.\n", file=sys.stderr)

    # Format and display report
    report = format_report(issues, das_results)
    print(report)
    
    # Save to file if requested
    if args.output:
        report_data = {
            'assessment_id': f"lint_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'instance_id': args.instance_id or 'static-only',
            'summary': {
                'total_rules': 28,
                'passed': 28 - len(issues),
                'critical': len([i for i in issues if i.get('severity') == 'critical']),
                'warnings': len([i for i in issues if i.get('severity') == 'warning']),
                'suggestions': len([i for i in issues if i.get('severity') == 'suggestion'])
            },
            'issues': issues,
            'das_results': das_results
        }
        
        with open(args.output, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Report saved to: {args.output}")
    
    # Exit code based on severity
    if args.fail_on:
        if args.fail_on == 'critical':
            if any(i.get('severity') == 'critical' for i in issues):
                sys.exit(1)
        elif args.fail_on == 'warning':
            if any(i.get('severity') in ('critical', 'warning') for i in issues):
                sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
