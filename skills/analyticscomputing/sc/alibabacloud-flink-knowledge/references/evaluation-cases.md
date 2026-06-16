# Evaluation Cases — alibabacloud-flink-knowledge Skill

This document contains the core evaluation cases and test step definitions for this Skill. Evaluation reports (`eval.result.*`) use these scenarios as the basis for judgment.

## CDC Multi-Table Sync (flink-cdc-mysql-sync)

**Test Steps**:
1. User requests generation of MySQL CDC multi-database/sharded-table sync SQL to Hologres
2. Expected: agent outputs complete CDAS syntax (including Source regex, Sink WITH configuration, routing logic)
3. Manual `CREATE TABLE + INSERT INTO` concatenation is prohibited

**Judgment Criteria**:
- SQL must use CDAS `CREATE DATABASE ... AS TABLE` syntax or equivalent
- Sink side must include complete WITH parameter configuration
- Source side must include multi-table matching logic (regex or full-table coverage)
- Non-standard syntax such as `TABLE(SOURCE())` is prohibited

## Checkpoint/Savepoint Restore (flink-checkpoint-savepoint-restore)

**Test Steps**:
1. User asks about considerations when adding new operators during job restoration from a Savepoint
2. Expected: agent distinguishes between stateless and stateful operator restoration differences
3. Must mention that `allowNonRestoredState` is a CLI startup parameter, not a SQL parameter

**Judgment Criteria**:
- Must clearly distinguish between the two operator types
- Must NOT use `SET 'allowNonRestoredState'` syntax
- Restoration strategy must be specific and actionable

## Backpressure Diagnosis (flink-backpressure-diagnosis)

**Test Steps**:
1. User reports a Flink job backpressure issue
2. Expected: agent provides standard troubleshooting steps (non-numeric)
3. Troubleshooting steps must carry G2 source labels

**Judgment Criteria**:
- Troubleshooting steps must be labeled [General Open-Source Standard] or [Alibaba Cloud Specific]
- Must NOT mix troubleshooting methods from different backends
- If specific threshold parameters are involved, they must be labeled as unverified

## SQL Kafka -> Hologres (flink-sql-kafka-to-hologres)

**Test Steps**:
1. User requests generation of Flink SQL from Kafka Source to Hologres Sink
2. Expected: agent outputs complete DDL + DML
3. Sink side must NOT include WATERMARK definitions

**Judgment Criteria**:
- SQL must conform to Flink DDL/DML syntax
- Sink table DDL must NOT contain WATERMARK
- Correct connector configuration must be used
