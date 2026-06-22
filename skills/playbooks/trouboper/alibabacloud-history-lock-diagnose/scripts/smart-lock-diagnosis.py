#!/usr/bin/env python3
"""
Smart lock wait diagnosis script
- Smart time range
- Targeted filtering
- Multi-batch concurrent fetching
"""

import subprocess
import json
import os
import re
import time
from datetime import datetime, timedelta
import concurrent.futures

class LockDiagnosisAnalyzer:
    def __init__(self, instance_id=None, region='cn-hangzhou'):
        """
        Initialize diagnoser
        
        Args:
            instance_id: Instance ID (rm-xxx or pc-xxx)
            region: Region (default cn-hangzhou)
        """
        self.instance_id = instance_id
        self.region = region
        self.endpoint = f'das.{region}.aliyuncs.com'
    
    def _call_das_api(self, action, **kwargs):
        """
        Call DAS API via aliyun CLI
        
        Args:
            action: API name (e.g. GetDasSQLLogHotData)
            **kwargs: API parameters (e.g. InstanceId, Start, End)
        
        Returns:
            dict: API response JSON data
        
        Raises:
            Exception: Raised when CLI call fails
        """
        raise NotImplementedError

    
    def extract_table_and_where(self, sql_text):
        """
        Extract table name and WHERE conditions
        
        Example:
        UPDATE accounts SET balance=1001 WHERE id=2 AND status='active'
        → {
            'table': 'accounts',
            'where_conditions': {'id': '2', 'status': 'active'}
          }
        """
        result = {
            'table': None,
            'where_conditions': {}
        }
        
        sql_upper = sql_text.upper()
        
        # Extract table name (INSERT must precede UPDATE: INSERT...ON DUPLICATE KEY UPDATE contains both keywords)
        if 'INSERT' in sql_upper:
            match = re.search(r'INSERT\s+INTO\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)

        elif 'UPDATE' in sql_upper:
            match = re.search(r'UPDATE\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)

        elif 'DELETE' in sql_upper:
            match = re.search(r'DELETE\s+FROM\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        elif 'SELECT' in sql_upper:
            match = re.search(r'FROM\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        # DDL statement table name extraction
        elif 'ALTER' in sql_upper:
            match = re.search(r'ALTER\s+TABLE\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        elif 'DROP' in sql_upper:
            match = re.search(r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        elif 'TRUNCATE' in sql_upper:
            match = re.search(r'TRUNCATE\s+(?:TABLE\s+)?(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        elif 'RENAME' in sql_upper:
            match = re.search(r'RENAME\s+TABLE\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        # FLUSH statement table name extraction
        elif 'FLUSH' in sql_upper:
            if 'WITH READ LOCK' in sql_upper or 'FOR EXPORT' in sql_upper:
                pass  # FTWRL / FOR EXPORT are global operations, no table name
            else:
                match = re.search(r'FLUSH\s+TABLES?\s+(\w+)', sql_text, re.IGNORECASE)
                if match and match.group(1).upper() not in ('WITH', 'READ', 'LOCK', 'FOR', 'EXPORT'):
                    result['table'] = match.group(1)
        
        # LOCK TABLES statement table name extraction
        elif 'LOCK' in sql_upper:
            match = re.search(r'LOCK\s+TABLES?\s+(\w+)', sql_text, re.IGNORECASE)
            if match:
                result['table'] = match.group(1)
        
        # Extract WHERE conditions (equality conditions)
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|;|$)', sql_text, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1)
            
            # Extract equality conditions: column = value
            eq_conditions = re.findall(r"(\w+)\s*=\s*['\"]?([^'\",\s]+)['\"]?", where_clause)
            for col, val in eq_conditions:
                result['where_conditions'][col] = val
        
        return result
    
    def query_sql_logs_by_where_condition(self, table_name, where_conditions, start_ms, end_ms, max_pages=5):
        """
        Query SQL logs by table name and WHERE conditions
        
        Server-side filtering using QueryKeyword + LogicalOperator=and:
        - When where_conditions is not None: QueryKeyword = 'column value table_name'
          e.g. UPDATE accounts WHERE id=1 -> QueryKeyword='id 1 accounts'
        - When where_conditions is None: QueryKeyword='table_name'
        """
        raise NotImplementedError

    
    def query_long_running_selects(self, table_name, start_ms, end_ms, min_latency_us=60000000, max_pages=5):
        """
        Query long-running SELECT on the same table (Latancy >= min_latency_us)
        
        For MDL lock diagnosis: long-running SELECT holds shared MDL lock, blocking ALTER TABLE etc.
        min_latency_us: Minimum execution time threshold, default 60s = 60,000,000 microseconds
        
        Note: No State filter, because killed long SELECT still held MDL lock before being killed.
        DAS API time filter may use SQL end time, caller should pass a wide enough End time.
        """
        raise NotImplementedError

    
    def query_table_selects(self, table_name, start_ms, end_ms, max_pages=5):
        """
        Query all SELECT statements on the same table (no Latancy filter)
        
        For MDL lock diagnosis: SELECT in transaction also holds shared MDL lock,
        if transaction is uncommitted, MDL lock is held until transaction ends.
        """
        raise NotImplementedError

    
    def query_sql_logs_by_keywords(self, start_ms, end_ms, keywords, max_pages=10):
        """Query SQL logs by keywords
        
        When all keywords are single words, use DAS API QueryKeyword for server-side pre-filtering,
        to avoid pagination truncation in large time windows (e.g. FLUSH operations truncated in 1-hour window).
        Multi-word keywords (e.g. 'for update') still use client-side filtering.
        """
        raise NotImplementedError

    
    def query_sql_logs_parallel(self, instance_id, problem_time):
        """Concurrently query multiple batches of SQL logs"""
        raise NotImplementedError

    
    def utc_to_beijing(self, utc_time_str):
        """Convert UTC time to Beijing time"""
        try:
            if utc_time_str.endswith('Z'):
                utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%S.%f')
            beijing_time = utc_time + timedelta(hours=8)
            return beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        except Exception:
            return utc_time_str

    def _calc_utc_seconds(self, utc_start, utc_end):
        """Calculate seconds between two UTC time strings"""
        try:
            start = utc_start.replace('Z', '').replace('T', ' ')
            end = utc_end.replace('Z', '').replace('T', ' ')
            dt_start = datetime.strptime(start[:26], '%Y-%m-%d %H:%M:%S.%f')
            dt_end = datetime.strptime(end[:26], '%Y-%m-%d %H:%M:%S.%f')
            return (dt_end - dt_start).total_seconds()
        except Exception:
            return None

    def _calc_logout_end_time(self, origin_time, latency_us):
        """Calculate transaction end time from logout! = OriginTime + Latancy

        logout! means session disconnect, MySQL auto-rolls back uncommitted transactions.
        Transaction end time = logout execution time + latency.
        """
        try:
            start_dt = datetime.strptime(origin_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
            end_dt = start_dt + timedelta(microseconds=int(latency_us))
            return end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        except Exception:
            return origin_time
    
    def _thread_has_serializable(self, sqls):
        """Check if SQL list contains SET transaction_isolation/tx_isolation = 'SERIALIZABLE'.
        Supports two syntaxes: SET transaction_isolation='SERIALIZABLE' and
        SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE。
        Returns the OriginTime of the SET statement if found, otherwise None."""
        for log in sqls:
            sql_lower = (log.get('SQLText', '') or '').lower()
            if ('set' in sql_lower and 'serializable' in sql_lower
                    and ('transaction_isolation' in sql_lower
                         or 'tx_isolation' in sql_lower
                         or 'transaction isolation' in sql_lower)):
                return log.get('OriginTime', '')
        return None

    def _classify_lock_type_label(self, lock_time, root_source=None, blocked_sql_text='', chain_members=None):
        """Output fine-grained lock type label based on context
        
        lock_time: LockTime of blocked SQL (microseconds)
        root_source: (tid, info) Lock holder thread info, info['sqls'] contains SQL list
        blocked_sql_text: Blocked SQL text
        chain_members: [(tid, info), ...] Intermediate chain members, for detecting FLUSH intermediate nodes
        
        Returns: Human-readable lock type label string
        """
        # Extract key DML SQL from lock holder thread
        root_sql = ''
        if root_source:
            _, root_info = root_source
            # Find key DML/SELECT from sqls list
            for s in root_info.get('sqls', []):
                sql_text = (s.get('SQLText') or '').strip()
                sql_upper = sql_text.upper()
                if any(kw in sql_upper for kw in ['DELETE', 'UPDATE', 'INSERT', 'SELECT', 'FLUSH']):
                    root_sql = sql_text
                    break
            # If sqls is empty (session_source scenario), get from session_info
            if not root_sql and root_info.get('session_source'):
                session_info = root_info.get('session_info', {})
                root_sql = session_info.get('SqlText', '') or ''
        
        root_sql_upper = root_sql.upper()
        blocked_upper = blocked_sql_text.upper().strip()
        
        if lock_time > 10000:
            # InnoDB row lock family
            # 0. SERIALIZABLE mode: plain SELECT adds shared Next-Key Lock
            if root_source:
                _, ri = root_source
                if ri.get('_serializable'):
                    return 'SERIALIZABLE Shared Next-Key Lock (S Lock)'
            # 1. Explicit locking: FOR UPDATE -> exclusive lock
            if 'FOR UPDATE' in root_sql_upper:
                return 'Exclusive Lock (X Lock)'
            # 2. Explicit locking: LOCK IN SHARE MODE / FOR SHARE -> shared lock
            if 'LOCK IN SHARE MODE' in root_sql_upper or 'FOR SHARE' in root_sql_upper:
                return 'Shared Lock (S Lock)'
            # 3. Range DELETE/UPDATE may produce gap lock (RR isolation level)
            #    Takes priority over INSERT intention lock, as range DML Gap Lock blocking INSERT is more common
            if any(kw in root_sql_upper for kw in ['DELETE', 'UPDATE']):
                # Check for range WHERE conditions
                where_pos = root_sql_upper.find('WHERE')
                if where_pos >= 0:
                    where_clause = root_sql_upper[where_pos:]
                    if any(op in where_clause for op in [' > ', ' < ', ' >= ', ' <= ', ' BETWEEN ']):
                        return 'Gap Lock'
            # 4. Blocker is INSERT -> INSERT intention lock (INSERT holds row lock blocking others)
            if root_sql_upper.lstrip().startswith('INSERT'):
                return 'INSERT Intention Lock'
            # 5. Default: record lock
            return 'Record Lock'
        else:
            # MDL lock family
            # 1. FLUSH operation (lock holder itself is FLUSH)
            if root_source:
                _, root_info = root_source
                if root_info.get('has_flush'):
                    return 'Flush Lock'
            if 'FLUSH' in root_sql_upper:
                return 'Flush Lock'
            # 2. Chain intermediate node contains FLUSH (lock holder holds MDL -> FLUSH waits exclusive MDL -> blocks diagnosed thread)
            if chain_members:
                for _, member_info in chain_members:
                    if member_info.get('has_flush'):
                        return 'Flush Lock'
            # 3. Blocked SQL itself is FLUSH (e.g. FLUSH TABLES / FLUSH TABLES WITH READ LOCK)
            if 'FLUSH' in blocked_upper:
                return 'Flush Lock'
            # 4. Default: MDL metadata lock
            return 'MDL (Metadata Lock)'

    def _render_thread_timeline(self, step_num, tid, info, role, problem_time_utc_str, indent='  ', lock_type='row'):
        """Render single thread transaction timeline in blocking chain
        
        lock_type: 'row' for InnoDB row lock, 'mdl' for MDL lock
        """
        num_label = chr(0x245F + step_num) if step_num <= 20 else f'[{step_num}]'
        print(f'{indent}{num_label} Thread {tid} ({role})')
        
        commit_time = info.get('commit_time')
        
        for log in info.get('sqls', []):
            sql_text = log.get('SQLText', '')
            sql_lower = sql_text.lower()
            origin_time = log.get('OriginTime', '')
            beijing_time = self.utc_to_beijing(origin_time)
            
            annotation = ''
            if any(kw in sql_lower for kw in ['begin', 'start transaction']):
                annotation = 'Begin transaction'
            elif 'set' in sql_lower and 'autocommit' in sql_lower and ('0' in sql_lower or 'off' in sql_lower):
                annotation = 'Disable autocommit, begin transaction'
            elif 'set' in sql_lower and 'innodb_lock_wait_timeout' in sql_lower:
                if lock_type == 'row':
                    annotation = 'Set InnoDB row lock wait timeout'
                else:
                    continue  # Skip row lock timeout in MDL lock scenario
            elif 'set' in sql_lower and 'lock_wait_timeout' in sql_lower:
                if lock_type == 'mdl':
                    annotation = 'Set MDL lock wait timeout'
                else:
                    continue  # Skip MDL timeout in row lock scenario
            elif 'set' in sql_lower and ('transaction_isolation' in sql_lower or 'tx_isolation' in sql_lower or 'transaction isolation' in sql_lower):
                annotation = 'Set transaction isolation level'
                if 'repeatable' in sql_lower:
                    annotation = 'Set isolation to RR (REPEATABLE-READ), Gap Lock enabled'
                elif 'committed' in sql_lower:
                    annotation = 'Set isolation to RC (READ-COMMITTED)'
                elif 'serializable' in sql_lower:
                    annotation = 'Set isolation to SERIALIZABLE, all SELECT auto-add shared Next-Key Lock'
            elif 'commit' in sql_lower and 'autocommit' not in sql_lower:
                annotation = 'Transaction committed'
            elif 'rollback' in sql_lower and 'autocommit' not in sql_lower:
                annotation = 'Transaction rolled back'
            elif 'logout' in sql_lower:
                latency_us = log.get('Latancy', 0) or 0
                annotation = f'Session disconnected, transaction auto-rolled back ({latency_us/1000000:.3f}s)'
            elif any(kw in sql_lower for kw in ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']):
                lock_time_val = log.get('LockTime', 0) or 0
                if lock_time_val < 100000:  # Lock acquired immediately (lock holder)
                    # Hold lock time = DML execution to transaction end (commit/rollback), or to problem time if uncommitted
                    end_ref = commit_time if commit_time else problem_time_utc_str
                    hold_secs = self._calc_utc_seconds(origin_time, end_ref)
                    if commit_time is None or commit_time > problem_time_utc_str:
                        annotation = f'Transaction uncommitted, holds lock {hold_secs:.0f}s' if hold_secs else 'Transaction uncommitted'
                    else:
                        annotation = f'Holds lock{hold_secs:.0f}s' if hold_secs else ''
                else:
                    annotation = f'Waits for lock LockTime={lock_time_val/1000000:.3f}s'
            elif 'lock tables' in sql_lower and 'unlock' not in sql_lower:
                annotation = 'Holds table write lock (MDL_SHARED_NO_READ_WRITE), blocks DML and SELECT'
            elif 'unlock tables' in sql_lower:
                annotation = 'Release table lock'
            elif 'flush' in sql_lower:
                latency_us = log.get('Latancy', 0) or 0
                if latency_us >= 1000000:  # >= 1s
                    latency_sec = latency_us / 1000000
                    annotation = f'FLUSH operation waiting {latency_sec:.1f}s (waiting for exclusive MDL, blocks subsequent DML)'
                else:
                    annotation = 'FLUSH operations'
            elif sql_lower.strip().startswith('select'):
                if info.get('_serializable'):
                    annotation = 'SERIALIZABLE mode SELECT auto-adds shared Next-Key Lock'
                else:
                    latency_us = log.get('Latancy', 0) or 0
                    if latency_us >= 5000000:
                        latency_sec = latency_us / 1000000
                        annotation = f'Long query {latency_sec:.1f}s, holds shared MDL lock'
            
            if annotation:
                print(f'{indent}  {beijing_time}  {sql_text}; {annotation}')
            else:
                print(f'{indent}  {beijing_time}  {sql_text}')
        print()
    
    def _render_blocking_chain(self, root_source, chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info=None, blocked_sql_audit=None, indent='  ', lock_type='row'):
        """Render blocking chain (transaction timeline format)
        
        blocked_sql_audit: Blocked SQL record from audit log (DAS), for actual execution time
        lock_type: 'row' for InnoDB row lock, 'mdl' for MDL lock
        """
        root_tid, root_info = root_source
        
        print(f'🔗 Blocking chain:')
        print()
        
        step = 1
        
        # ① lock holder
        self._render_thread_timeline(step, root_tid, root_info, 'lock holder', problem_time_utc_str, indent, lock_type=lock_type)
        step += 1
        
        # Intermediate blocked threads
        for tid, info in chain_members:
            self._render_thread_timeline(step, tid, info, 'blocked', problem_time_utc_str, indent, lock_type=lock_type)
            step += 1
        
        # diagnosed thread
        num_label = chr(0x245F + step) if step <= 20 else f'[{step}]'
        print(f'{indent}{num_label} Thread {thread_id} (diagnosed thread)')
        # Show diagnosed thread's transaction context (e.g. SET innodb_lock_wait_timeout, BEGIN)
        if blocked_thread_info and blocked_thread_info.get('sqls'):
            for log in blocked_thread_info['sqls']:
                log_sql = log.get('SQLText', '')
                log_lower = log_sql.lower()
                # Skip DML (will show separately with audit time below)
                if any(kw in log_lower for kw in ['update', 'delete', 'insert', 'replace']):
                    continue
                beijing_time = self.utc_to_beijing(log.get('OriginTime', ''))
                annotation = ''
                if any(kw in log_lower for kw in ['begin', 'start transaction']):
                    annotation = 'Begin transaction'
                elif 'set' in log_lower and 'autocommit' in log_lower:
                    annotation = 'Disable autocommit, begin transaction'
                elif 'set' in log_lower and 'innodb_lock_wait_timeout' in log_lower:
                    if lock_type == 'row':
                        annotation = 'Set InnoDB row lock wait timeout'
                    else:
                        continue  # Skip row lock timeout in MDL lock scenario
                elif 'set' in log_lower and 'lock_wait_timeout' in log_lower:
                    if lock_type == 'mdl':
                        annotation = 'Set MDL lock wait timeout'
                    else:
                        continue  # Skip MDL timeout in row lock scenario
                elif 'set' in log_lower and ('transaction_isolation' in log_lower or 'tx_isolation' in log_lower or 'transaction isolation' in log_lower):
                    annotation = 'Set transaction isolation level'
                    if 'repeatable' in log_lower:
                        annotation = 'Set isolation to RR (REPEATABLE-READ), Gap Lock enabled'
                    elif 'committed' in log_lower:
                        annotation = 'Set isolation to RC (READ-COMMITTED)'
                    elif 'serializable' in log_lower:
                        annotation = 'Set isolation to SERIALIZABLE, all SELECT auto-add shared Next-Key Lock'
                if annotation:
                    print(f'{indent}  {beijing_time}  {log_sql}; {annotation}')
                else:
                    print(f'{indent}  {beijing_time}  {log_sql}')
        # Blocked SQL: prefer actual execution time from audit log
        audit_time_resolved = None
        audit_sql_resolved = sql
        # Priority 1: From blocked_sql_audit (timeout record)
        if blocked_sql_audit and str(blocked_sql_audit.get('ThreadID', '')) == str(thread_id):
            audit_time_resolved = self.utc_to_beijing(blocked_sql_audit.get('OriginTime', ''))
            audit_sql_resolved = blocked_sql_audit.get('SQLText', '') or sql
        # Priority 2: Extract DML audit time from blocked_thread_info's SQL list
        if not audit_time_resolved and blocked_thread_info and blocked_thread_info.get('sqls'):
            for log in blocked_thread_info['sqls']:
                log_sql = log.get('SQLText', '')
                log_lower = log_sql.lower()
                if any(kw in log_lower for kw in ['update', 'delete', 'insert', 'replace']):
                    audit_time_resolved = self.utc_to_beijing(log.get('OriginTime', ''))
                    audit_sql_resolved = log_sql or sql
                    break
        if audit_time_resolved:
            print(f'{indent}  {audit_time_resolved}  {audit_sql_resolved}; lock wait timeout')
        else:
            print(f'{indent}  {problem_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}  {sql}; lock wait timeout')
        print()
    
    def _try_deadlock_cli(self, victim_sql, table_name, where_conditions, problem_time, problem_time_utc_str):
        """Get deadlock details via aliyun CLI. Returns True on success, False on failure.

        CLI flow: CreateLatestDeadLockAnalysis -> GetDeadLockHistory -> GetDeadLockDetail
        In inner mode, _call_das_api returns empty data for unknown actions, auto return False.
        """
        victim_thread = str(victim_sql.get('ThreadID', ''))

        print('=' * 120)
        print('Step 3: Deadlock diagnosis (via DAS CLI)')
        print('=' * 120)
        print()

        # Step 1: Trigger DAS latest deadlock analysis
        try:
            print('   🔄 Triggering DAS deadlock analysis...')
            self._call_das_api('CreateLatestDeadLockAnalysis',
                               InstanceId=self.instance_id)
        except Exception as e:
            print(f'   ⚠️  CreateLatestDeadLockAnalysis failed: {e}')
            return False

        # Step 2: Query deadlock history
        # DAS time filter is based on gmtCreate (record creation time), not lockTime (deadlock time)
        # gmtCreate can be hours later than lockTime, so use a wide time window
        start_ms = int((problem_time - timedelta(hours=1)).timestamp() * 1000)
        end_ms = int((problem_time + timedelta(hours=24)).timestamp() * 1000)
        try:
            history = self._call_das_api('GetDeadLockHistory',
                                         InstanceId=self.instance_id,
                                         StartTime=str(start_ms),
                                         EndTime=str(end_ms))
        except Exception as e:
            print(f'   ⚠️  GetDeadLockHistory failed: {e}')
            return False

        records = history.get('Data', {}).get('list', [])
        if not records:
            print('   ⚠️  No deadlock records found in time range')
            return False

        # Find record with lockTime closest to user time, validate time diff
        target_time_ms = int(problem_time.timestamp() * 1000)
        best = min(records, key=lambda r: abs(r.get('lockTime', 0) - target_time_ms))
        time_diff_sec = abs(best.get('lockTime', 0) - target_time_ms) / 1000
        text_id = best.get('textId')
        if not text_id:
            print('   ⚠️  Deadlock record missing textId')
            return False

        if time_diff_sec > 60:
            print(f'   ⚠️  DAS deadlock record time diff {time_diff_sec:.0f}s（> 60s），may not be the same deadlock')
            return False

        print(f'   ✅ Found deadlock record: textId={text_id}（time diff {time_diff_sec:.1f}s）')

        # Step 3: Get deadlock detail
        try:
            detail = self._call_das_api('GetDeadLockDetail',
                                        InstanceId=self.instance_id,
                                        TextId=text_id)
        except Exception as e:
            print(f'   ⚠️  GetDeadLockDetail failed: {e}')
            return False

        deadlock_json = detail.get('Data', {}).get('deadlock', '')
        if not deadlock_json:
            print('   ⚠️  Deadlock detail is empty')
            return False

        import json as _json
        deadlock = _json.loads(deadlock_json) if isinstance(deadlock_json, str) else deadlock_json
        transactions = deadlock.get('transactions', [])
        if len(transactions) < 2:
            print('   ⚠️  Insufficient deadlock transactions')
            return False

        # Step 4: Parse victim / winner
        rollback_trx = str(deadlock.get('rollbackTrxId', ''))
        victim_trx = None
        winner_trx = None
        for trx in transactions:
            if str(trx.get('trxIdInLock', '')) == rollback_trx:
                victim_trx = trx
            else:
                winner_trx = trx
        if not victim_trx or not winner_trx:
            victim_trx, winner_trx = transactions[1], transactions[0]

        winner_thread = winner_trx.get('threadId', '')
        victim_thread_cli = victim_trx.get('threadId', '')
        winner_sql_text = (winner_trx.get('sqlText', '') or '').strip()
        victim_sql_text_cli = (victim_trx.get('sqlText', '') or '').strip()
        occur_time_ms = deadlock.get('occurTime', 0)

        # Validate: DAS deadlock involves user-provided thread
        all_thread_ids = {str(trx.get('threadId', '')) for trx in transactions}
        if victim_thread not in all_thread_ids:
            print(f'   ⚠️  DAS deadlock record does not contain user thread {victim_thread}（involved threads: {all_thread_ids}），may not be the same deadlock')
            return False

        print(f'   ✅ Deadlock transaction count: {len(transactions)}')
        print(f'   Winner: Thread {winner_thread}, SQL: {winner_sql_text}')
        print(f'   Victim: Thread {victim_thread_cli}, SQL: {victim_sql_text_cli}')
        print()

        # Extract all involved resource id values
        all_ids = set()
        all_where_keys = set()
        for trx in transactions:
            sql_t = (trx.get('sqlText', '') or '').strip()
            parsed = self.extract_table_and_where(sql_t)
            if parsed.get('where_conditions'):
                for k, v in parsed['where_conditions'].items():
                    all_where_keys.add(k)
                    all_ids.add(str(v))
        if all_where_keys and all_ids:
            key = sorted(all_where_keys)[0]
            resource_str = f'{key}={",".join(sorted(all_ids))}'
        elif where_conditions:
            key = list(where_conditions.keys())[0]
            resource_str = f'{key}={where_conditions[key]}'
        else:
            resource_str = ''

        # Extract lock info from DAS data
        winner_hold = winner_trx.get('holdLockMode', '')
        winner_wait = winner_trx.get('waitLockMode', '')
        victim_hold = victim_trx.get('holdLockMode', '')
        victim_wait = victim_trx.get('waitLockMode', '')

        # Time conversion
        if occur_time_ms:
            from datetime import datetime as _dt, timezone as _tz
            occur_dt = _dt.fromtimestamp(occur_time_ms / 1000, tz=_tz.utc)
            occur_beijing = (occur_dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        else:
            occur_beijing = self.utc_to_beijing(victim_sql.get('OriginTime', ''))

        detected_table = table_name
        for trx in transactions:
            tables = trx.get('relatedTables', [])
            if tables:
                detected_table = tables[0].replace('`', '').split('.')[-1]
                break

        # Render timeline (compatible with validator parser)
        print('=' * 120)
        print('Step 5: Deadlock transaction details (DAS CLI)')
        print('=' * 120)
        print()

        print(f'  ① Thread {winner_thread} (lock holder)')
        print(f'    {occur_beijing}  {winner_sql_text};')
        if winner_hold:
            print(f'    Holds lock: {winner_hold}')
        if winner_wait:
            print(f'    Waits for lock: {winner_wait}')
        print()

        print(f'  ② Thread {victim_thread_cli} (rolled back)')
        print(f'    {occur_beijing}  {victim_sql_text_cli};')
        if victim_hold:
            print(f'    Holds lock: {victim_hold}')
        if victim_wait:
            print(f'    Waits for lock: {victim_wait}')
        print()

        # Step 6: Diagnosis conclusion
        print('=' * 120)
        print('Step 6: Diagnosis conclusion')
        print('=' * 120)
        print()
        print(f'   1. Lock type: Deadlock')
        print(f'   2. Deadlock cycle:')

        # Extract resources held by each party
        winner_parsed = self.extract_table_and_where(winner_sql_text)
        victim_parsed = self.extract_table_and_where(victim_sql_text_cli)
        w_where = ','.join(f'{k}={v}' for k, v in winner_parsed.get('where_conditions', {}).items())
        v_where = ','.join(f'{k}={v}' for k, v in victim_parsed.get('where_conditions', {}).items())
        if w_where and v_where:
            print(f'      Thread {winner_thread} holds {v_where} → requests {w_where}')
            print(f'      Thread {victim_thread_cli} holds {w_where} → requests {v_where}')
        else:
            print(f'      Thread {winner_thread} ↔ Thread {victim_thread_cli} cross lock wait')
        print(f'   3. Victim（rolled back）: Thread {victim_thread_cli}')
        print(f'   4. Winner（acquired lock）: Thread {winner_thread}')
        print(f'   5. Table: {detected_table}')
        if resource_str:
            print(f'   6. WHERE conditions: {{{resource_str}}}')
        print()
        print(f'   💡 Recommendations:')
        print(f'      - Check application code for table {detected_table}  concurrent DML, unify lock acquisition order')
        print(f'      - Consider shortening transaction length to reduce deadlock probability')
        print(f'      - Catch Error 1213 in application layer and auto-retry')
        return True

    def _diagnose_deadlock(self, victim_sql, table_name, where_conditions, problem_time, problem_time_utc_str):
        """Deadlock diagnosis: try CLI first, fallback to SQL audit inference on failure."""
        import concurrent.futures

        # Try CLI first (external mode uses aliyun CLI; inner mode _call_das_api returns empty, auto fallback)
        if self._try_deadlock_cli(victim_sql, table_name, where_conditions, problem_time, problem_time_utc_str):
            return

        print()
        print('   ⚠️  CLI did not return deadlock details, switching to SQL audit inference mode')
        print()

        victim_thread = str(victim_sql.get('ThreadID', ''))
        victim_origin = victim_sql.get('OriginTime', '')
        victim_sql_text = victim_sql.get('SQLText', '') or ''

        print('=' * 120)
        print('Step 3: Deadlock diagnosis (SQL audit inference)')
        print('=' * 120)
        print()
        print(f'🔍 Detected deadlock victim: Thread {victim_thread}, State=1213')
        print(f'   SQL: {victim_sql_text}')
        print(f'   Time: {self.utc_to_beijing(victim_origin)}')
        print()

        # Query all DML on same table (time window [-30s, +10s], deadlock is instantaneous)
        start_ms = int((problem_time - timedelta(seconds=30)).timestamp() * 1000)
        end_ms = int((problem_time + timedelta(seconds=10)).timestamp() * 1000)

        candidate_logs = self.query_sql_logs_by_keywords(
            start_ms, end_ms, [table_name], max_pages=5
        )
        print(f'   Same-table DML query: found {len(candidate_logs)}  ')

        # Identify winner: same-table DML, not victim thread, LockTime > 0, State=0
        # Core logic: InnoDB resolves deadlock instantly - rolls back victim and grants lock to winner
        # Therefore winner OriginTime is nearly identical to victim OriginTime (diff < 2s)
        winner = None
        best_time_diff = 999
        for log in candidate_logs:
            log_thread = str(log.get('ThreadID', ''))
            if log_thread == victim_thread:
                continue
            log_lock_time = log.get('LockTime', 0) or 0
            log_state = str(log.get('State', ''))
            log_sql = (log.get('SQLText', '') or '').lower()
            if log_lock_time > 0 and log_state in ('0', '') and table_name.lower() in log_sql:
                log_origin = log.get('OriginTime', '')
                if log_origin and victim_origin:
                    td = abs(self._calc_utc_seconds(log_origin, victim_origin))
                    if td < 3 and td < best_time_diff:
                        best_time_diff = td
                        winner = log

        if not winner:
            # Relax time window to 10s
            for log in candidate_logs:
                log_thread = str(log.get('ThreadID', ''))
                if log_thread == victim_thread:
                    continue
                log_lock_time = log.get('LockTime', 0) or 0
                log_state = str(log.get('State', ''))
                log_sql = (log.get('SQLText', '') or '').lower()
                if log_lock_time > 0 and log_state in ('0', '') and table_name.lower() in log_sql:
                    log_origin = log.get('OriginTime', '')
                    if log_origin and victim_origin:
                        td = abs(self._calc_utc_seconds(log_origin, victim_origin))
                        if td < 10 and td < best_time_diff:
                            best_time_diff = td
                            winner = log

        if not winner:
            print('   ⚠️  No deadlock winner thread found (no same-table, same-timewindow successful DML)')
            print()
            print('=' * 120)
            print('Step 6: Diagnosis conclusion')
            print('=' * 120)
            print()
            print(f'   1. Lock type: Deadlock')
            print(f'   2. Victim（rolled back）: Thread {victim_thread}')
            print(f'   3. Winner: undetermined (no matching lock wait thread in audit data)')
            print(f'   4. Table: {table_name}')
            if where_conditions:
                wc_key = list(where_conditions.keys())[0]
                print(f'   5. WHERE conditions: {{{wc_key}={where_conditions[wc_key]}}}')
            return

        winner_thread = str(winner.get('ThreadID', ''))
        winner_origin = winner.get('OriginTime', '')
        winner_sql_text = winner.get('SQLText', '') or ''
        winner_lock_time = (winner.get('LockTime', 0) or 0) / 1000000

        print(f'   ✅ Found deadlock winner: Thread {winner_thread}')
        print(f'      SQL: {winner_sql_text}')
        print(f'      LockTime: {winner_lock_time:.3f}s')
        print()

        # Query full SQL sequences for both transactions
        tx_start_ms = int((problem_time - timedelta(minutes=5)).timestamp() * 1000)
        tx_end_ms = end_ms

        print('Step 4: Query both transaction SQL sequences')
        print()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_victim = executor.submit(
                self.query_thread_dml_on_table, victim_thread, table_name, tx_start_ms, tx_end_ms, 3
            )
            future_winner = executor.submit(
                self.query_thread_dml_on_table, winner_thread, table_name, tx_start_ms, tx_end_ms, 3
            )
            victim_sqls = future_victim.result()
            winner_sqls = future_winner.result()

        print(f'   Thread {victim_thread} (victim): {len(victim_sqls)}   DML')
        print(f'   Thread {winner_thread} (winner): {len(winner_sqls)}   DML')
        print()

        # Query transaction control statements
        try:
            tc_logs = self.query_transaction_controls(
                [victim_thread, winner_thread], tx_start_ms, tx_end_ms, max_pages=3
            )
        except Exception:
            tc_logs = []

        # Build both transaction timelines
        def build_thread_info(thread, dml_logs, tc):
            sqls = []
            for log in tc:
                if str(log.get('ThreadID', '')) == thread:
                    sqls.append(log)
            for log in dml_logs:
                sqls.append(log)
            sqls.sort(key=lambda x: x.get('OriginTime', ''))
            return {'sqls': sqls, 'commit_time': None}

        victim_info = build_thread_info(victim_thread, victim_sqls, tc_logs)
        winner_info = build_thread_info(winner_thread, winner_sqls, tc_logs)

        # Extract WHERE conditions for both parties (collect all involved id values)
        all_ids = set()
        all_where_keys = set()
        for log in victim_sqls + winner_sqls:
            sql_t = log.get('SQLText', '') or ''
            parsed = self.extract_table_and_where(sql_t)
            if parsed.get('where_conditions'):
                for k, v in parsed['where_conditions'].items():
                    all_where_keys.add(k)
                    all_ids.add(str(v))

        # Format: id=1,2 (consistent with row lock output format)
        if all_where_keys and all_ids:
            key = sorted(all_where_keys)[0]
            resource_str = f'{key}={",".join(sorted(all_ids))}'
        elif where_conditions:
            key = list(where_conditions.keys())[0]
            resource_str = f'{key}={where_conditions[key]}'
        else:
            resource_str = ''

        # Step 5: Render timeline
        print('=' * 120)
        print('Step 5: Transaction timeline')
        print('=' * 120)
        print()

        self._render_thread_timeline(1, winner_thread, winner_info, 'lock holder', problem_time_utc_str, lock_type='row')
        self._render_thread_timeline(2, victim_thread, victim_info, 'rolled back', problem_time_utc_str, lock_type='row')

        # Step 6: Diagnosis conclusion
        print('=' * 120)
        print('Step 6: Diagnosis conclusion')
        print('=' * 120)
        print()
        print(f'   1. Lock type: Deadlock')
        print(f'   2. Deadlock cycle:')
        # Extract first-locked resources from winner/victim SQL
        winner_first_where = ''
        victim_first_where = ''
        for log in winner_sqls:
            p = self.extract_table_and_where(log.get('SQLText', '') or '')
            if p.get('where_conditions'):
                winner_first_where = ','.join(f'{k}={v}' for k, v in p['where_conditions'].items())
                break
        for log in victim_sqls:
            p = self.extract_table_and_where(log.get('SQLText', '') or '')
            if p.get('where_conditions'):
                victim_first_where = ','.join(f'{k}={v}' for k, v in p['where_conditions'].items())
                break
        if winner_first_where and victim_first_where:
            print(f'      Thread {winner_thread} holds {winner_first_where} → requests {victim_first_where}')
            print(f'      Thread {victim_thread} holds {victim_first_where} → requests {winner_first_where}')
        else:
            print(f'      Thread {winner_thread} ↔ Thread {victim_thread} cross lock wait')
        print(f'   3. Victim（rolled back）: Thread {victim_thread}')
        print(f'   4. Winner（acquired lock）: Thread {winner_thread}')
        print(f'   5. Table: {table_name}')
        if resource_str:
            print(f'   6. WHERE conditions: {{{resource_str}}}')
        print()
        print(f'   💡 Recommendations:')
        print(f'      - Check application code for table {table_name}  concurrent DML, unify lock acquisition order')
        print(f'      - Consider shortening transaction length to reduce deadlock probability')
        print(f'      - Catch Error 1213 in application layer and auto-retry')

    def _commit_match_fallback(self, table_name, blocked_sql, lock_ref_utc_str,
                               lock_time, problem_time, thread_id):
        """COMMIT-match: Search for COMMIT/ROLLBACK/LOGOUT at lock release time to locate lock holder thread.

        For State=0 (SQL succeeded, lock released at OriginTime+LockTime) and
        State=1205 (lock wait timeout, lock holder may COMMIT/ROLLBACK around timeout).
        Returns (root_source, chain_members) or (None, []).
        """
        blocked_state = str(blocked_sql.get('State', '') or '0')
        if blocked_state not in ('0', '', '1205'):
            return None, []

        try:
            ref_dt = datetime.strptime(lock_ref_utc_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
        except Exception:
            return None, []

        lock_time_sec = lock_time / 1000000.0
        lock_wait_start_dt = ref_dt - timedelta(seconds=lock_time_sec)

        ref_ms = int((ref_dt - datetime(1970, 1, 1)).total_seconds() * 1000)
        lock_time_ms = int(lock_time_sec * 1000)
        lock_release_ms = ref_ms + lock_time_ms

        lock_release_dt = ref_dt + timedelta(seconds=lock_time_sec)
        lock_release_utc_str = lock_release_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        print(f'  🔍 COMMIT-match: Searching lock release time ({self.utc_to_beijing(lock_release_utc_str)}) nearby TC events...')
        print(f'     (blocked SQL start={self.utc_to_beijing(lock_ref_utc_str)}, LockTime={lock_time_sec:.3f}s)')

        tc_logs = self.query_tc_without_thread_filter(lock_release_ms - 15000, lock_release_ms + 5000, max_pages=5)
        if not tc_logs:
            print(f'  ⚠️  COMMIT-match: No TC events found in [-15s,+5s] around lock release time')
            return None, []

        # Exclude diagnosed thread, calculate distance (from lock release time)
        candidates = []
        for log in tc_logs:
            tid = str(log.get('ThreadID', ''))
            if tid == str(thread_id):
                continue
            origin = log.get('OriginTime', '')
            sql_lower = (log.get('SQLText', '') or '').lower()
            if 'logout' in sql_lower:
                effective_time = self._calc_logout_end_time(origin, log.get('Latancy', 0) or 0)
            else:
                effective_time = origin
            calc = self._calc_utc_seconds(effective_time, lock_release_utc_str)
            dist = abs(calc) if calc is not None else 999
            candidates.append((dist, tid, log, effective_time))

        candidates.sort(key=lambda x: x[0])
        print(f'  📋 COMMIT-match: Found {len(candidates)}  TC candidates (lock release [-15s,+5s] window)')

        # Verify top N candidates (expanded to top 10, deduplicate same thread)
        seen_threads = set()
        validate_list = []
        for item in candidates:
            tid = item[1]
            if tid not in seen_threads:
                seen_threads.add(tid)
                validate_list.append(item)
            if len(validate_list) >= 10:
                break
        for dist, cand_tid, tc_log, eff_time in validate_list:
            tc_sql = (tc_log.get('SQLText', '') or '').strip()
            print(f'    Candidate thread {cand_tid}: {tc_sql} @ {self.utc_to_beijing(eff_time)} (dist={dist:.3f}s)')

            # Trace back DML history for this thread on target table
            lws_ms = int((lock_wait_start_dt - datetime(1970, 1, 1)).total_seconds() * 1000)
            dml_start = lws_ms - 30 * 60 * 1000
            dml_end = lock_release_ms + 5000
            thread_dmls = self.query_thread_dml_on_table(
                cand_tid, table_name, dml_start, dml_end, max_pages=5)

            # Supplement complete TC (needed for both DML and SERIALIZABLE detection)
            full_tc = self.query_transaction_controls({cand_tid}, dml_start, dml_end, max_pages=5)

            is_serializable = False
            lock_sqls = thread_dmls  # DML or SERIALIZABLE SELECT

            # Check SERIALIZABLE (regardless of DML presence)
            serializable_time = self._thread_has_serializable(full_tc)

            if not thread_dmls:
                # No DML -> must be SERIALIZABLE + SELECT to be lock holder
                if serializable_time:
                    thread_selects = self.query_thread_select_on_table(
                        cand_tid, table_name, dml_start, dml_end, max_pages=3)
                    if thread_selects:
                        print(f'    ✅ Thread {cand_tid} uses SERIALIZABLE,'
                              f'on {table_name}: {len(thread_selects)} SELECT (shared Next-Key Lock)')
                        is_serializable = True
                        lock_sqls = thread_selects
                    else:
                        print(f'    → Thread {cand_tid} is SERIALIZABLE but on {table_name}  no SELECT, skipping')
                        continue
                else:
                    print(f'    → Thread {cand_tid} on {table_name}: no DML and not SERIALIZABLE, skipping')
                    continue
            elif serializable_time:
                is_serializable = True

            lock_sqls.sort(key=lambda x: x.get('OriginTime', ''))
            first_lock_sql = lock_sqls[0]
            first_lock_time = first_lock_sql.get('OriginTime', '')

            if is_serializable and not thread_dmls:
                lock_type_desc = 'SELECT (SERIALIZABLE shared Next-Key Lock)'
            elif is_serializable:
                lock_type_desc = 'DML (SERIALIZABLE isolation level)'
            else:
                lock_type_desc = 'DML'
            print(f'    ✅ Thread {cand_tid} on {table_name}: {len(lock_sqls)} {lock_type_desc},'
                  f'earliest: {self.utc_to_beijing(first_lock_time)}')

            # Build root_source
            all_thread_sqls = lock_sqls + [tc_log]
            existing_keys = set(
                (str(l.get('ThreadID', '')), l.get('OriginTime', ''), l.get('SQLText', ''))
                for l in all_thread_sqls
            )
            for l in full_tc:
                if str(l.get('ThreadID', '')) == cand_tid:
                    key = (str(l.get('ThreadID', '')), l.get('OriginTime', ''), l.get('SQLText', ''))
                    if key not in existing_keys:
                        all_thread_sqls.append(l)
                        existing_keys.add(key)
            all_thread_sqls.sort(key=lambda x: x.get('OriginTime', ''))

            root_info = {
                'started': False,
                'has_dml': True,
                'dml_time': first_lock_time,
                'commit_time': eff_time,
                'lock_time': first_lock_sql.get('LockTime', 0) or 0,
                'sqls': all_thread_sqls,
                'transaction_id': first_lock_sql.get('TransactionId', ''),
                '_logout_end_time': None,
                '_serializable': is_serializable,
            }
            for sq in all_thread_sqls:
                sql_l = (sq.get('SQLText', '') or '').lower()
                if any(kw in sql_l for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                    root_info['started'] = True

            suffix = ' (SERIALIZABLE)' if is_serializable else ''
            print(f'  ✅ COMMIT-match confirmed lock holder thread{suffix}: {cand_tid}')
            return (cand_tid, root_info), []

        print(f'  ⚠️  COMMIT-match: all candidates failed verification')
        return None, []

    def query_transaction_controls(self, thread_ids, start_ms, end_ms, max_pages=3):
        """
        Query transaction control statements for specified threads (BEGIN/COMMIT/ROLLBACK/SET autocommit)
        Server-side filter using ThreadID parameter
        """
        raise NotImplementedError

    def query_tc_without_thread_filter(self, start_ms, end_ms, max_pages=3):
        """Query COMMIT/ROLLBACK/LOGOUT events (all threads) for COMMIT-match technique."""
        raise NotImplementedError

    def query_thread_dml_on_table(self, thread_id, table_name, start_ms, end_ms, max_pages=3):
        """Query DML operations for specified threads on target table, for COMMIT-match verification."""
        raise NotImplementedError

    def query_thread_select_on_table(self, thread_id, table_name, start_ms, end_ms, max_pages=3):
        """Query plain SELECT for specified threads on target table (exclude FOR UPDATE/LOCK IN SHARE MODE).
        For detecting SERIALIZABLE isolation level where SELECT auto-adds shared Next-Key Lock."""
        raise NotImplementedError

    def query_serializable_threads(self, start_ms, end_ms, max_pages=2):
        """Query all SET ... SERIALIZABLE statements in time window, return involved thread IDs."""
        raise NotImplementedError

    def query_all_sessions(self):
        """Query all current sessions using GetMySQLAllSessionAsync

        This is a read-only operation, no database credentials required.
        Fallback when audit log cannot find lock holder, check active sessions.

        Returns: SessionData dict or None
        """
        raise NotImplementedError


    def _find_mdl_holder_from_sessions(self, session_data, table_name, blocked_thread_id):
        """Find sessions that may hold MDL lock from current sessions
        
        Returns: (session_info, reason) or (None, None)
        """
        if not session_data:
            return None, None
        
        session_list = session_data.get('SessionList', [])
        if not session_list:
            return None, None
        
        candidates = []
        for s in session_list:
            sid = str(s.get('SessionId', ''))
            if sid == str(blocked_thread_id):
                continue
            
            trx_duration = s.get('TrxDuration', 0) or 0
            exec_time = s.get('Time', 0) or 0
            command = s.get('Command', '')
            state = s.get('State', '')
            sql_text = s.get('SqlText', '') or ''
            db_name = s.get('DbName', '')
            
            # Candidate 1: Long transaction (>5s, may hold shared MDL lock)
            if trx_duration > 5:
                reason = f'Uncommitted transaction ({trx_duration}s)'
                if table_name and table_name.lower() in sql_text.lower():
                    reason += f', involves table {table_name}'
                    candidates.append((s, reason, 100 + trx_duration))  # High priority
                else:
                    candidates.append((s, reason, trx_duration))
            
            # Candidate 2: Long-running query (may hold shared MDL lock)
            elif command == 'Query' and exec_time > 10:
                if table_name and table_name.lower() in sql_text.lower():
                    reason = f'Long-running query ({exec_time}s), involves table {table_name}'
                    candidates.append((s, reason, 50 + exec_time))
            
            # Candidate 3: Sleep state with uncommitted transaction
            elif command == 'Sleep' and trx_duration > 5:
                reason = f'Sleep with uncommitted transaction ({trx_duration}s)'
                candidates.append((s, reason, trx_duration))
        
        if not candidates:
            return None, None
        
        # Sort by priority, return most likely candidate
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][0], candidates[0][1]

    def diagnose(self, instance_id, problem_time_str, thread_id, sql):
        """Full diagnosis flow (optimized: WHERE condition precise matching + fast query)"""
        import time as _time
        diag_start = _time.time()
        
        print('=' * 120)
        print('🎯 Smart lock wait diagnosis (fast & precise)')
        print('=' * 120)
        print()
        
        # Parse time (Beijing time)
        problem_time = datetime.strptime(problem_time_str, '%Y-%m-%d %H:%M:%S.%f')
        
        print(f'📌 Diagnosis args:')
        print(f'   Instance ID: {instance_id}')
        print(f'   Problem time: {problem_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} (Beijing time)')
        print(f'   blockedThread: {thread_id}')
        print(f'   blocked SQL: {sql}')
        print()

        # Pre-check: verify SQL Insight and hot data are enabled
        try:
            config = self._call_das_api('DescribeSqlLogConfig', InstanceId=instance_id)
            data = config.get('Data', {})
            sql_log_enable = data.get('SqlLogEnable', False)
            hot_enable = data.get('HotEnable', False)
            hot_retention = data.get('HotRetention', 0)
            cold_enable = data.get('ColdEnable', False)
            cold_retention = data.get('ColdRetention', 0)

            if not sql_log_enable:
                print('❌ SQL Insight (SQL Audit) is NOT enabled on this instance.')
                print('   Enable it via DAS Console: https://das.console.aliyun.com/')
                print('   Reference: https://help.aliyun.com/zh/das/user-guide/sql-insight')
                return

            if not hot_enable or hot_retention <= 0:
                print(f'❌ SQL Insight hot data is NOT available (HotEnable={hot_enable}, HotRetention={hot_retention}d).')
                print('   This skill requires hot data (GetDasSQLLogHotData) to query audit records.')
                print('   Enable hot storage via DAS Console: https://das.console.aliyun.com/')
                return

            hot_expired = False
            hot_boundary = datetime.now() - timedelta(days=hot_retention)
            if problem_time < hot_boundary:
                hot_expired = True
                days_ago = (datetime.now() - problem_time).days
                print(f'⚠️  Problem time ({problem_time_str}) is {days_ago} days ago, exceeds hot data retention ({hot_retention}d).')
                print(f'   Hot data available from: {hot_boundary.strftime("%Y-%m-%d %H:%M:%S")}')
                print('   Audit data for this time may be unavailable. Diagnosis may return incomplete results.')

            print(f'✅ SQL Insight enabled (hot: {hot_retention}d, cold: {cold_retention}d)')
        except PermissionError:
            hot_expired = False
            print('⚠️  Cannot check SQL Insight config (permission denied), proceeding anyway...')
        except Exception as e:
            hot_expired = False
            print(f'⚠️  Cannot check SQL Insight config ({e}), proceeding anyway...')
        print()

        # Step 1: Extract table name and WHERE conditions from user SQL
        print('=' * 120)
        print('Step 1: Extract table and WHERE conditions from user SQL')
        print('=' * 120)
        print()
        
        extracted = self.extract_table_and_where(sql)
        table_name = extracted['table']
        where_conditions = extracted['where_conditions']
        
        print(f'📋 Extracted info:')
        print(f'   Table: {table_name}')
        print(f'   WHERE conditions: {where_conditions if where_conditions else "None"}')
        print()
        
        # Step 2: Query blocked SQL (narrowed time range: +/-5 minutes)
        print('=' * 120)
        print('Step 2: Query blocked SQL (+/-5 minutes)')
        print('=' * 120)
        print()
        
        self.instance_id = instance_id
        start_ms_1205 = int((problem_time - timedelta(minutes=5)).timestamp() * 1000)
        end_ms_1205 = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
        
        blocked_sqls = self.query_sql_logs_by_keywords(start_ms_1205, end_ms_1205, [])
        blocked_sqls = [
            log for log in blocked_sqls
            if str(log.get('State', '')) in ['1205', '1213', '1317']
        ]
        blocked_sqls = sorted(blocked_sqls, key=lambda x: x.get('OriginTime', ''))
        
        print(f'✅ Found {len(blocked_sqls)}  blocked SQL')
        print()
        
        # Find blocked SQL matching user-specified thread
        target_blocked = None
        for log in blocked_sqls:
            if str(log.get('ThreadID', '')) == str(thread_id):
                target_blocked = log
                break
        
        # If batch query found nothing, use ThreadID for targeted query
        if not target_blocked:
            print(f'   ℹ️  Batch query did not find thread {thread_id}  timeout record, performing targeted query...')
            targeted_start = int((problem_time - timedelta(minutes=10)).timestamp() * 1000)
            targeted_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
            targeted_data = self._call_das_api('GetDasSQLLogHotData',
                InstanceId=instance_id,
                Start=str(targeted_start),
                End=str(targeted_end),
                ThreadID=str(thread_id),
                SortKey='OriginTime',
                SortMethod='DESC',
                PageNumbers='1',
                MaxRecordsPerPage='100',
            )
            targeted_logs = targeted_data.get('Data', {}).get('List', [])
            # First find timeout/killed SQL for this thread (State:1205/1317)
            for log in targeted_logs:
                if str(log.get('State', '')) in ['1205', '1213', '1317']:
                    target_blocked = log
                    break
            # If no timeout record, find successful DML with lock wait for this thread
            # Scenario: SQL succeeded but experienced lock wait (LockTime > 0)
            if not target_blocked:
                for log in targeted_logs:
                    log_lock_time = log.get('LockTime', 0)
                    log_sql_type = (log.get('SQLText', '') or '').strip().split()[0].upper() if log.get('SQLText') else ''
                    if log_lock_time > 0 and log_sql_type in ('UPDATE', 'DELETE', 'INSERT', 'SELECT', 'REPLACE'):
                        target_blocked = log
                        print(f'   ✅ FoundThread {thread_id}  successful execution record (LockTime={log_lock_time/1000000:.3f}s，SQL succeeded but experienced lock wait)')
                        break
            # If still not found, search FLUSH/DDL SQL (MDL lock wait not recorded in LockTime)
            # Scenario: FLUSH TABLES / ALTER TABLE MDL lock wait, LockTime=0 and not DML
            if not target_blocked:
                user_sql_first_word = sql.strip().split()[0].upper() if sql else ''
                for log in targeted_logs:
                    log_sql_text = (log.get('SQLText', '') or '').strip()
                    log_sql_type = log_sql_text.split()[0].upper() if log_sql_text else ''
                    if log_sql_type in ('FLUSH', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME', 'LOCK') and log_sql_type == user_sql_first_word:
                        target_blocked = log
                        print(f'   ✅ Found thread {thread_id} {log_sql_type} record (MDL lock wait not recorded in LockTime)')
                        break
            # Deadlock: State=1213 SQL rolled back by InnoDB immediately, LockTime=0
            if not target_blocked:
                for log in targeted_logs:
                    if str(log.get('State', '')) == '1213':
                        target_blocked = log
                        print(f'   ✅ FoundThread {thread_id}  deadlock record (State=1213, InnoDB rollback)')
                        break
            if target_blocked and target_blocked not in blocked_sqls:
                print(f'   ✅ FoundThread {thread_id}  audit record: {self.utc_to_beijing(target_blocked.get("OriginTime", ""))}')
            elif not target_blocked:
                print(f'   ⚠️  Thread {thread_id} related records not found')
            print()
        
        if not target_blocked and not blocked_sqls:
            print('❌ No blocked SQL or diagnosed thread records found, cannot continue diagnosis')
            if hot_expired:
                print(f'   Likely cause: problem time exceeds hot data retention ({hot_retention}d). Audit data has expired.')
                print(f'   Hot data available from: {hot_boundary.strftime("%Y-%m-%d %H:%M:%S")}')
                print('   Solution: invoke this skill within the hot data retention window after the lock wait occurs.')
            return
        
        blocked_sql = target_blocked or blocked_sqls[0]
        lock_time = blocked_sql.get('LockTime', 0)
        
        print(f'📋 blocked SQL:')
        print(f'   Time: {self.utc_to_beijing(blocked_sql.get("OriginTime", ""))}')
        print(f'   Thread: {blocked_sql.get("ThreadID", "")}')
        print(f'   LockTime: {lock_time / 1000000:.3f} s')
        blocked_state_str = str(blocked_sql.get('State', ''))
        if blocked_state_str == '1213':
            lock_type_label = 'Deadlock'
        elif lock_time > 10000:
            lock_type_label = 'InnoDB Row Lock'
        else:
            lock_type_label = 'MDL Lock'
        print(f'   Lock type: {lock_type_label}')
        print(f'   SQL: {blocked_sql.get("SQLText", "")}')
        print()
        
        # Step 3: Select strategy based on lock type
        all_logs = []
        batch_results = {}
        lock_source_threads = []
        root_source = None
        blocked_in_chain = []
        thread_transactions = {}
        
        # Convert problem time to UTC for comparison
        problem_time_utc = problem_time - timedelta(hours=8)
        problem_time_utc_str = problem_time_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # Row lock branch reference time: use actual OriginTime from DAS (SQL completion time)
        # instead of user-provided approximate time, as OriginTime is the precise completion moment
        # MDL branch already uses ddl_start_utc_str correctly, this only affects row lock branch
        lock_ref_utc_str = blocked_sql.get('OriginTime', problem_time_utc_str)

        # Deadlock detection: State=1213 means InnoDB detected deadlock and rolled back
        blocked_state = str(blocked_sql.get('State', ''))
        if blocked_state == '1213':
            self._diagnose_deadlock(blocked_sql, table_name, where_conditions, problem_time, problem_time_utc_str)
            return

        if where_conditions and table_name and lock_time > 10000:
            # Has WHERE conditions + Table + InnoDB row lock: precise WHERE matching
            # Note: MDL lock (lock_time <= 10000) goes to MDL analysis even with WHERE conditions
            print('=' * 120)
            print('Step 3: WHERE condition precise matching (fast mode)')
            print('=' * 120)
            print()
            
            # Auto-expand time range strategy: -10min -> -30min -> -2h
            time_ranges = [
                (timedelta(minutes=10), timedelta(minutes=5), 5, '[-10min, +5min]'),
                (timedelta(minutes=30), timedelta(minutes=5), 8, '[-30min, +5min]'),
                (timedelta(hours=2), timedelta(minutes=5), 10, '[-2h, +5min]'),
            ]
            
            lock_source_sqls = []
            root_source = None
            blocked_in_chain = []
            
            for back_delta, fwd_delta, max_pages, range_desc in time_ranges:
                start_ms_where = int((problem_time - back_delta).timestamp() * 1000)
                end_ms_where = int((problem_time + fwd_delta).timestamp() * 1000)
                
                print(f'🎯 Strategy: Query {table_name}  for SQL with same WHERE conditions')
                print(f'   WHERE conditions: {where_conditions}')
                print(f'   Time range: {range_desc}，max {max_pages}  pages')
                print()
                
                lock_source_sqls = self.query_sql_logs_by_where_condition(
                    table_name, where_conditions, start_ms_where, end_ms_where, max_pages=max_pages
                )
                
                # Deduplicate
                seen_keys = set()
                deduped_sqls = []
                for log in lock_source_sqls:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_sqls.append(log)
                lock_source_sqls = deduped_sqls
                
                print(f'✅ Found {len(lock_source_sqls)}   related SQL (deduplicated)')
                print()
                
                if not lock_source_sqls:
                    print('⚠️  No related SQL found')
                    if range_desc != time_ranges[-1][3]:
                        print('   Expanding time range and retrying...')
                        print()
                    continue
                
                # Time overlap analysis
                all_logs = lock_source_sqls
                batch_results['WHERE precise matching'] = lock_source_sqls
                
                # Collect transaction control statements for related threads
                related_thread_ids = set(str(log.get('ThreadID')) for log in lock_source_sqls)
                related_thread_ids.add(str(thread_id))
                
                tc_start = int((problem_time - back_delta).timestamp() * 1000)
                tc_end = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                tc_logs = self.query_transaction_controls(related_thread_ids, tc_start, tc_end)
                
                # Deduplicate TC logs
                seen_tc = set()
                deduped_tc = []
                for log in tc_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_tc:
                        seen_tc.add(key)
                        deduped_tc.append(log)
                tc_logs = deduped_tc
                
                # Merge and analyze transaction state
                all_thread_logs = lock_source_sqls + tc_logs
                thread_transactions = {}
                for log in sorted(all_thread_logs, key=lambda x: x.get('OriginTime', '')):
                    tid = str(log.get('ThreadID', ''))
                    sql_text = log.get('SQLText', '').lower()
                    transaction_id = log.get('TransactionId', '')
                    origin_time = log.get('OriginTime', '')
                    
                    if tid not in thread_transactions:
                        thread_transactions[tid] = {
                            'started': False,
                            'has_dml': False,
                            '_is_serializable': False,
                            'dml_time': None,
                            'commit_time': None,
                            'lock_time': 0,
                            'sqls': [],
                            'transaction_id': transaction_id,
                            '_logout_end_time': None
                        }

                    # Session boundary: SQL after logout belongs to new session, reset transaction state
                    # Consecutive logout records are same disconnect (DAS may return duplicates), no reset
                    logout_end = thread_transactions[tid].get('_logout_end_time')
                    if logout_end and origin_time > logout_end and 'logout' not in sql_text:
                        thread_transactions[tid]['started'] = False
                        thread_transactions[tid]['has_dml'] = False
                        thread_transactions[tid]['_is_serializable'] = False
                        thread_transactions[tid]['dml_time'] = None
                        thread_transactions[tid]['commit_time'] = None
                        thread_transactions[tid]['lock_time'] = 0
                        thread_transactions[tid]['_logout_end_time'] = None
                        thread_transactions[tid]['transaction_id'] = transaction_id

                    thread_transactions[tid]['sqls'].append(log)

                    if any(kw in sql_text for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                        thread_transactions[tid]['started'] = True
                        thread_transactions[tid]['has_dml'] = False
                        thread_transactions[tid]['dml_time'] = None
                        thread_transactions[tid]['commit_time'] = None
                        thread_transactions[tid]['lock_time'] = 0

                    if any(kw in sql_text for kw in ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']):
                        thread_transactions[tid]['has_dml'] = True
                        if not thread_transactions[tid]['dml_time']:
                            thread_transactions[tid]['dml_time'] = origin_time
                            thread_transactions[tid]['lock_time'] = log.get('LockTime', 0) or 0

                    # SERIALIZABLE detection: plain SELECT auto-adds shared Next-Key Lock
                    if ('set' in sql_text
                            and ('transaction_isolation' in sql_text or 'tx_isolation' in sql_text
                                 or 'transaction isolation' in sql_text)
                            and 'serializable' in sql_text):
                        thread_transactions[tid]['_is_serializable'] = True

                    if any(kw in sql_text for kw in ['commit', 'rollback']) and 'autocommit' not in sql_text:
                        if not thread_transactions[tid]['commit_time']:
                            thread_transactions[tid]['commit_time'] = origin_time

                    # logout! means session disconnect, MySQL auto-rolls back uncommitted transactions
                    # Transaction end time = logout execution time + latency
                    if 'logout' in sql_text:
                        latency_us = log.get('Latancy', 0) or 0
                        logout_end_time = self._calc_logout_end_time(origin_time, latency_us)
                        if not thread_transactions[tid]['commit_time']:
                            thread_transactions[tid]['commit_time'] = logout_end_time
                        thread_transactions[tid]['_logout_end_time'] = logout_end_time

                # SERIALIZABLE supplement: for threads with _is_serializable=True but has_dml=False, query SELECT to fill dml_time
                for tid, info in thread_transactions.items():
                    if info.get('_is_serializable') and not info['has_dml'] and tid != str(thread_id):
                        sel_start = int((problem_time - back_delta).timestamp() * 1000)
                        sel_end = int((problem_time + fwd_delta).timestamp() * 1000)
                        thread_selects = self.query_thread_select_on_table(
                            tid, table_name, sel_start, sel_end, max_pages=3)
                        if thread_selects:
                            thread_selects.sort(key=lambda x: x.get('OriginTime', ''))
                            info['has_dml'] = True
                            info['_serializable'] = True
                            info['dml_time'] = thread_selects[0].get('OriginTime', '')
                            info['lock_time'] = thread_selects[0].get('LockTime', 0) or 0
                            existing_keys = set(
                                (str(l.get('ThreadID', '')), l.get('OriginTime', ''), l.get('SQLText', ''))
                                for l in info['sqls'])
                            for sel_log in thread_selects:
                                key = (str(sel_log.get('ThreadID', '')), sel_log.get('OriginTime', ''), sel_log.get('SQLText', ''))
                                if key not in existing_keys:
                                    info['sqls'].append(sel_log)
                                    existing_keys.add(key)
                            info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                            print(f'  ✅ Thread {tid} uses SERIALIZABLE,on {table_name}: {len(thread_selects)} SELECT (shared Next-Key Lock)')

                # Lock holder determination logic:
                # Last successful SQL operating on same row before problem time = lock holder
                # （Successful execution means lock acquired, transaction spanning problem time means lock still held）
                LOCK_TIME_THRESHOLD = 100000  # 100ms
                root_source = None
                blocked_in_chain = []

                for tid, info in thread_transactions.items():
                    if not info['has_dml']:
                        continue
                    if tid == str(thread_id):
                        continue
                    
                    dml_time = info['dml_time']
                    commit_time = info['commit_time']
                    lock_time_val = info['lock_time']
                    
                    if dml_time and dml_time < lock_ref_utc_str:
                        # DML successfully executed before blocked SQL completed
                        if (commit_time is None or commit_time > lock_ref_utc_str):
                            # Transaction spans blocked time (uncommitted or committed after blocked SQL completed)
                            if lock_time_val < LOCK_TIME_THRESHOLD:
                                # Take the latest (closest to problem time = most likely direct lock holder)
                                if root_source is None or dml_time > root_source[1]['dml_time']:
                                    root_source = (tid, info)
                            else:
                                blocked_in_chain.append((tid, info))
                    elif dml_time and dml_time >= lock_ref_utc_str:
                        blocked_in_chain.append((tid, info))
                
                if root_source:
                    break  # Found lock holder, stop expanding
                
                # No lock holder found, try expanding time range
                if range_desc != time_ranges[-1][3]:
                    print(f'⚠️  Not found in {range_desc}  lock holder, auto-expanding time range...')
                    print()
            
            # Display results
            print('=' * 120)
            print('Step 4: Time overlap analysis results')
            print('=' * 120)
            print()
            print(f'  Problem time (UTC): {problem_time_utc_str}')
            print(f'  Lock holder ref time (UTC): {lock_ref_utc_str}  (Blocked SQL DAS OriginTime)')
            print(f'  Lock holder criteria: Last successful SQL on same row before blocked SQL completed, with transaction spanning blocked time')
            print()
            
            if root_source:
                root_tid, root_info = root_source
                lock_source_threads = [root_tid]
                
                # Query TC statements for lock holder thread separately (ensure BEGIN/COMMIT found)
                has_tc = any(
                    any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit', 'commit', 'rollback', 'logout'])
                    for log in root_info['sqls']
                )
                if not has_tc:
                    tc_start_root = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                    tc_end_root = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                    root_tc_logs = self.query_transaction_controls({root_tid}, tc_start_root, tc_end_root, max_pages=5)
                    if root_tc_logs:
                        existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in root_info['sqls'])
                        for log in root_tc_logs:
                            if str(log.get('ThreadID', '')) == root_tid:
                                key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                if key not in existing_keys:
                                    root_info['sqls'].append(log)
                                    existing_keys.add(key)
                                    sql_lower = log.get('SQLText', '').lower()
                                    if any(kw in sql_lower for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                                        root_info['started'] = True
                                    if any(kw in sql_lower for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower:
                                        if not root_info['commit_time']:
                                            root_info['commit_time'] = log.get('OriginTime', '')
                                    # logout! = Session disconnected, transaction auto-rolled back
                                    if 'logout' in sql_lower:
                                        if not root_info['commit_time']:
                                            latency_us = log.get('Latancy', 0) or 0
                                            root_info['commit_time'] = self._calc_logout_end_time(log.get('OriginTime', ''), latency_us)
                        root_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                
                # Re-validate lock holder: if supplemental query shows commit before blocked SQL completed, invalidate
                if root_info['commit_time'] and root_info['commit_time'] <= lock_ref_utc_str:
                    print(f'  ⚠️  Thread {root_tid} transaction committed at {self.utc_to_beijing(root_info["commit_time"])} (before problem time), excluding, reselecting...')
                    print()
                    
                    # Add current invalid root_source to exclusion list, re-traverse all candidates
                    excluded_tids = {root_tid}
                    root_source = None
                    lock_source_threads = []
                    
                    # Re-traverse thread_transactions for next lock holder candidate
                    retry_candidates = []
                    for tid, info in thread_transactions.items():
                        if tid in excluded_tids or tid == str(thread_id):
                            continue
                        if not info['has_dml']:
                            continue
                        dml_time = info['dml_time']
                        commit_time_c = info['commit_time']
                        lock_time_val = info['lock_time']
                        if dml_time and dml_time < lock_ref_utc_str:
                            if (commit_time_c is None or commit_time_c > lock_ref_utc_str):
                                if lock_time_val < LOCK_TIME_THRESHOLD:
                                    retry_candidates.append((tid, info))
                    
                    # Query TC for each candidate separately and verify
                    for cand_tid, cand_info in sorted(retry_candidates, key=lambda x: x[1]['dml_time'], reverse=True):
                        cand_has_tc = any(
                            (any(kw in log.get('SQLText', '').lower() for kw in ['commit', 'rollback'])
                            and 'autocommit' not in log.get('SQLText', '').lower())
                            or 'logout' in log.get('SQLText', '').lower()
                            for log in cand_info['sqls']
                        )
                        if not cand_has_tc:
                            tc_start_c = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                            tc_end_c = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                            cand_tc_logs = self.query_transaction_controls({cand_tid}, tc_start_c, tc_end_c, max_pages=3)
                            if cand_tc_logs:
                                existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in cand_info['sqls'])
                                for log in cand_tc_logs:
                                    if str(log.get('ThreadID', '')) == cand_tid:
                                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                        if key not in existing_keys:
                                            cand_info['sqls'].append(log)
                                            existing_keys.add(key)
                                            sql_lower = log.get('SQLText', '').lower()
                                            if any(kw in sql_lower for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                                                cand_info['started'] = True
                                            if any(kw in sql_lower for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower:
                                                if not cand_info['commit_time']:
                                                    cand_info['commit_time'] = log.get('OriginTime', '')
                                            # logout! = Session disconnected, transaction auto-rolled back
                                            if 'logout' in sql_lower:
                                                if not cand_info['commit_time']:
                                                    latency_us = log.get('Latancy', 0) or 0
                                                    cand_info['commit_time'] = self._calc_logout_end_time(log.get('OriginTime', ''), latency_us)
                                cand_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                        
                        # Verify candidate is still valid
                        if cand_info['commit_time'] is None or cand_info['commit_time'] > lock_ref_utc_str:
                            root_source = (cand_tid, cand_info)
                            root_tid, root_info = root_source
                            lock_source_threads = [root_tid]
                            break
                
                # Supplement TC statements for blocked threads in chain
                if root_source:
                    for i, (chain_tid, chain_info) in enumerate(blocked_in_chain):
                        chain_has_tc = any(
                            any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit', 'commit', 'rollback', 'logout'])
                            for log in chain_info['sqls']
                        )
                        if not chain_has_tc:
                            tc_start_chain = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                            tc_end_chain = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                            chain_tc_logs = self.query_transaction_controls({chain_tid}, tc_start_chain, tc_end_chain, max_pages=3)
                            if chain_tc_logs:
                                existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in chain_info['sqls'])
                                for log in chain_tc_logs:
                                    if str(log.get('ThreadID', '')) == chain_tid:
                                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                        if key not in existing_keys:
                                            chain_info['sqls'].append(log)
                                            existing_keys.add(key)
                                            sql_lower = log.get('SQLText', '').lower()
                                            if any(kw in sql_lower for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower:
                                                if not chain_info['commit_time']:
                                                    chain_info['commit_time'] = log.get('OriginTime', '')
                                            # logout! = Session disconnected, transaction auto-rolled back
                                            if 'logout' in sql_lower:
                                                if not chain_info['commit_time']:
                                                    latency_us = log.get('Latancy', 0) or 0
                                                    chain_info['commit_time'] = self._calc_logout_end_time(log.get('OriginTime', ''), latency_us)
                                chain_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                
                if not root_source:
                    print('⚠️  All lock holder candidates committed, auto-querying current sessions...')
                    print()
                    
                    # Fallback: call GetMySQLAllSessionAsync
                    try:
                        session_data = self.query_all_sessions()
                        if session_data:
                            total = session_data.get('TotalSessionCount', 0)
                            active = session_data.get('ActiveSessionCount', 0)
                            print(f'  ℹ️  Current sessions: total {total} , active {active} ')
                            
                            holder_session, holder_reason = self._find_mdl_holder_from_sessions(session_data, table_name, thread_id)
                            if holder_session:
                                holder_sid = holder_session.get('SessionId', '')
                                print(f'  ✅ Found possible lock holder via live session query:')
                                print(f'     Session ID: {holder_sid}')
                                print(f'     User: {holder_session.get("User", "")}')
                                print(f'     Exec time: {holder_session.get("Time", 0)}s')
                                print(f'     Trx duration: {holder_session.get("TrxDuration", 0)}s')
                                print(f'     SQL: {(holder_session.get("SqlText", "") or "")[:200]}')
                                print(f'     Reason: {holder_reason}')
                                print()
                                
                                lock_source_threads = [str(holder_sid)]
                                root_source = (str(holder_sid), {
                                    'started': True, 'has_dml': True,
                                    'dml_time': None, 'commit_time': None,
                                    'lock_time': 0, 'sqls': [],
                                    'transaction_id': holder_session.get('TrxId', ''),
                                    'session_source': True,
                                    'session_info': holder_session,
                                    'session_reason': holder_reason
                                })
                            else:
                                print('  ⚠️  No clear lock holder found in current sessions either')
                                print()
                    except Exception as e:
                        print(f'  ⚠️  GetMySQLAllSessionAsync Query failed: {e}')
                        print()
            
            # Display verified results
            if root_source:
                root_tid, root_info = root_source
                lock_source_threads = [root_tid]
                
                # Filter intermediate blocked threads
                chain_members = []
                root_dml_time = root_info['dml_time']
                for tid, info in blocked_in_chain:
                    dml_time = info.get('dml_time', '')
                    lock_time_val = info.get('lock_time', 0)
                    if dml_time and root_dml_time < dml_time < lock_ref_utc_str and lock_time_val >= 100000:
                        chain_members.append((tid, info))
                chain_members.sort(key=lambda x: x[1].get('dml_time', ''))
                
                # Get diagnosed thread transaction context
                blocked_thread_info = thread_transactions.get(str(thread_id))
                
                # Supplement TC for diagnosed thread (e.g. SET innodb_lock_wait_timeout)
                if blocked_thread_info is None:
                    blocked_thread_info = {'sqls': []}
                    thread_transactions[str(thread_id)] = blocked_thread_info
                bt_has_tc = any(
                    any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit', 'innodb_lock_wait_timeout', 'lock_wait_timeout'])
                    for log in blocked_thread_info.get('sqls', [])
                )
                if not bt_has_tc:
                    bt_tc_start = int((problem_time - timedelta(minutes=10)).timestamp() * 1000)
                    bt_tc_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                    bt_tc_logs = self.query_transaction_controls({str(thread_id)}, bt_tc_start, bt_tc_end, max_pages=3)
                    if bt_tc_logs:
                        existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in blocked_thread_info.get('sqls', []))
                        for log in bt_tc_logs:
                            if str(log.get('ThreadID', '')) == str(thread_id):
                                key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                if key not in existing_keys:
                                    blocked_thread_info['sqls'].append(log)
                                    existing_keys.add(key)
                        blocked_thread_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                
                # Render blocking chain (transaction timeline format)
                self._render_blocking_chain(root_source, chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info, blocked_sql_audit=target_blocked, lock_type='row' if lock_time > 10000 else 'mdl')
            
            else:
                # WHERE precise matching did not find lock holder, falling back to full table DML query
                # Scenario: non-indexed column UPDATE blocked by full table DELETE, different WHERE conditions yield no results
                print('⚠️  WHERE precise matching did not find lock holder, falling back to full table DML query...')
                print(f'   （Lock holder may be full table scan or SQL with different WHERE conditions）')
                print()
                
                # No WHERE filter, query all DML on same table
                start_ms_table = int((problem_time - timedelta(hours=2)).timestamp() * 1000)
                end_ms_table = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                
                table_all_sqls = self.query_sql_logs_by_where_condition(
                    table_name, None, start_ms_table, end_ms_table, max_pages=10
                )
                
                # Deduplicate
                seen_keys = set()
                deduped_table_sqls = []
                for log in table_all_sqls:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_table_sqls.append(log)
                table_all_sqls = deduped_table_sqls
                
                print(f'✅ Full table DML found {len(table_all_sqls)}  (deduplicated)')
                print()

                # Supplement LOCK TABLES query (table locks also cause LockTime > 0 in row lock path)
                lt_start_ms = int((problem_time - timedelta(hours=1)).timestamp() * 1000)
                lt_end_ms = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                lock_table_sqls = self.query_sql_logs_by_keywords(lt_start_ms, lt_end_ms, ['lock tables'])
                if lock_table_sqls:
                    lt_dedup_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in table_all_sqls)
                    for log in lock_table_sqls:
                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                        if key not in lt_dedup_keys:
                            table_all_sqls.append(log)
                            lt_dedup_keys.add(key)
                    print(f'  ✅ Supplement LOCK TABLES query found {len(lock_table_sqls)}  ')
                    print()

                if table_all_sqls:
                    all_logs = table_all_sqls
                    batch_results['WHERE precise matching'] = table_all_sqls

                    # Re-collect thread transaction control
                    related_thread_ids = set(str(log.get('ThreadID')) for log in table_all_sqls)
                    related_thread_ids.add(str(thread_id))

                    tc_start = int((problem_time - timedelta(hours=2)).timestamp() * 1000)
                    tc_end = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)

                    try:
                        ser_tids = self.query_serializable_threads(tc_start, tc_end)
                        new_ser = ser_tids - related_thread_ids
                        if new_ser:
                            print(f'  🔍 Found {len(new_ser)}  SERIALIZABLE Thread: {", ".join(sorted(new_ser))}')
                            related_thread_ids.update(new_ser)
                    except NotImplementedError:
                        pass

                    tc_logs = self.query_transaction_controls(related_thread_ids, tc_start, tc_end)

                    seen_tc = set()
                    deduped_tc = []
                    for log in tc_logs:
                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                        if key not in seen_tc:
                            seen_tc.add(key)
                            deduped_tc.append(log)
                    tc_logs = deduped_tc
                    
                    # Merge analysis
                    all_thread_logs = table_all_sqls + tc_logs
                    thread_transactions = {}
                    for log in sorted(all_thread_logs, key=lambda x: x.get('OriginTime', '')):
                        tid = str(log.get('ThreadID', ''))
                        sql_text = log.get('SQLText', '').lower()
                        transaction_id = log.get('TransactionId', '')
                        origin_time = log.get('OriginTime', '')

                        if tid not in thread_transactions:
                            thread_transactions[tid] = {
                                'started': False, 'has_dml': False,
                                'has_lock_table': False,
                                '_is_serializable': False,
                                'dml_time': None, 'commit_time': None,
                                'lock_time': 0, 'sqls': [],
                                'transaction_id': transaction_id,
                                '_logout_end_time': None
                            }

                        # Session boundary detection
                        logout_end = thread_transactions[tid].get('_logout_end_time')
                        if logout_end and origin_time > logout_end and 'logout' not in sql_text:
                            thread_transactions[tid]['started'] = False
                            thread_transactions[tid]['has_dml'] = False
                            thread_transactions[tid]['_is_serializable'] = False
                            thread_transactions[tid]['dml_time'] = None
                            thread_transactions[tid]['commit_time'] = None
                            thread_transactions[tid]['lock_time'] = 0
                            thread_transactions[tid]['_logout_end_time'] = None
                            thread_transactions[tid]['transaction_id'] = transaction_id

                        thread_transactions[tid]['sqls'].append(log)

                        if any(kw in sql_text for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                            thread_transactions[tid]['started'] = True
                            thread_transactions[tid]['has_dml'] = False
                            thread_transactions[tid]['dml_time'] = None
                            thread_transactions[tid]['commit_time'] = None
                            thread_transactions[tid]['lock_time'] = 0

                        if any(kw in sql_text for kw in ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']):
                            thread_transactions[tid]['has_dml'] = True
                            if not thread_transactions[tid]['dml_time']:
                                thread_transactions[tid]['dml_time'] = origin_time
                                thread_transactions[tid]['lock_time'] = log.get('LockTime', 0) or 0

                        # SERIALIZABLE detection
                        if ('set' in sql_text
                                and ('transaction_isolation' in sql_text or 'tx_isolation' in sql_text
                                     or 'transaction isolation' in sql_text)
                                and 'serializable' in sql_text):
                            thread_transactions[tid]['_is_serializable'] = True

                        if any(kw in sql_text for kw in ['commit', 'rollback']) and 'autocommit' not in sql_text:
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = origin_time

                        if 'lock tables' in sql_text and 'unlock' not in sql_text:
                            thread_transactions[tid]['has_lock_table'] = True
                            if not thread_transactions[tid]['dml_time']:
                                thread_transactions[tid]['dml_time'] = origin_time

                        if 'unlock tables' in sql_text:
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = origin_time

                        if 'logout' in sql_text:
                            latency_us = log.get('Latancy', 0) or 0
                            logout_end_time = self._calc_logout_end_time(origin_time, latency_us)
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = logout_end_time
                            thread_transactions[tid]['_logout_end_time'] = logout_end_time

                    # SERIALIZABLE supplement: query SELECT to set dml_time
                    for tid, info in thread_transactions.items():
                        if info.get('_is_serializable') and not info['has_dml'] and tid != str(thread_id):
                            sel_start = int((problem_time - timedelta(hours=2)).timestamp() * 1000)
                            sel_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                            thread_selects = self.query_thread_select_on_table(
                                tid, table_name, sel_start, sel_end, max_pages=3)
                            if thread_selects:
                                thread_selects.sort(key=lambda x: x.get('OriginTime', ''))
                                info['has_dml'] = True
                                info['_serializable'] = True
                                info['dml_time'] = thread_selects[0].get('OriginTime', '')
                                info['lock_time'] = thread_selects[0].get('LockTime', 0) or 0
                                existing_keys = set(
                                    (str(l.get('ThreadID', '')), l.get('OriginTime', ''), l.get('SQLText', ''))
                                    for l in info['sqls'])
                                for sel_log in thread_selects:
                                    key = (str(sel_log.get('ThreadID', '')), sel_log.get('OriginTime', ''), sel_log.get('SQLText', ''))
                                    if key not in existing_keys:
                                        info['sqls'].append(sel_log)
                                        existing_keys.add(key)
                                info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                                print(f'  ✅ Thread {tid} uses SERIALIZABLE,on {table_name}: {len(thread_selects)} SELECT (shared Next-Key Lock)')

                    # Time overlap analysis
                    LOCK_TIME_THRESHOLD = 100000
                    fallback_root = None
                    fallback_blocked = []

                    try:
                        _ref_dt2 = datetime.strptime(lock_ref_utc_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                        _lws_dt2 = _ref_dt2 - timedelta(seconds=lock_time / 1000000.0)
                        lock_wait_start_utc_str = _lws_dt2.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    except Exception:
                        lock_wait_start_utc_str = lock_ref_utc_str

                    for tid, info in thread_transactions.items():
                        if not info['has_dml'] and not info.get('has_lock_table'):
                            continue
                        if tid == str(thread_id):
                            continue

                        dml_time = info['dml_time']
                        commit_time = info['commit_time']
                        lock_time_val = info['lock_time']

                        if dml_time and dml_time < lock_ref_utc_str:
                            if (commit_time is None or commit_time > lock_ref_utc_str):
                                if lock_time_val < LOCK_TIME_THRESHOLD:
                                    if fallback_root is None:
                                        fallback_root = (tid, info)
                                    else:
                                        cur_before = fallback_root[1]['dml_time'] <= lock_wait_start_utc_str
                                        new_before = dml_time <= lock_wait_start_utc_str
                                        if new_before and not cur_before:
                                            fallback_root = (tid, info)
                                        elif new_before == cur_before and dml_time > fallback_root[1]['dml_time']:
                                            fallback_root = (tid, info)
                                else:
                                    fallback_blocked.append((tid, info))
                        elif dml_time and dml_time >= lock_ref_utc_str:
                            fallback_blocked.append((tid, info))

                    if fallback_root:
                        root_source = fallback_root
                        blocked_in_chain = fallback_blocked
                        root_tid, root_info = root_source
                        lock_source_threads = [root_tid]
                        
                        # Query TC statements for lock holder thread separately (ensure BEGIN/COMMIT found)
                        has_tc = any(
                            any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit', 'commit', 'rollback'])
                            for log in root_info['sqls']
                        )
                        if not has_tc:
                            tc_start_root = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                            tc_end_root = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                            root_tc_logs = self.query_transaction_controls({root_tid}, tc_start_root, tc_end_root, max_pages=5)
                            if root_tc_logs:
                                existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in root_info['sqls'])
                                for log in root_tc_logs:
                                    if str(log.get('ThreadID', '')) == root_tid:
                                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                        if key not in existing_keys:
                                            root_info['sqls'].append(log)
                                            existing_keys.add(key)
                                            sql_lower = log.get('SQLText', '').lower()
                                            if any(kw in sql_lower for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                                                root_info['started'] = True
                                            if any(kw in sql_lower for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower:
                                                if not root_info['commit_time']:
                                                    root_info['commit_time'] = log.get('OriginTime', '')
                                root_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                        
                        # Re-validate: if commit before blocked SQL completed, lock holder is invalid
                        if root_info['commit_time'] and root_info['commit_time'] <= lock_ref_utc_str:
                            root_source = None
                            lock_source_threads = []
                        
                        if root_source:
                            # Filter intermediate blocked threads
                            chain_members = []
                            root_dml_time = root_info['dml_time']
                            for tid_c, info_c in fallback_blocked:
                                dml_time_c = info_c.get('dml_time', '')
                                lock_time_c = info_c.get('lock_time', 0)
                                if dml_time_c and root_dml_time < dml_time_c < lock_ref_utc_str and lock_time_c >= 100000:
                                    chain_members.append((tid_c, info_c))
                            chain_members.sort(key=lambda x: x[1].get('dml_time', ''))
                            
                            # Get diagnosed thread transaction context
                            blocked_thread_info = thread_transactions.get(str(thread_id))
                            
                            # Supplement TC for diagnosed thread (e.g. SET innodb_lock_wait_timeout)
                            if blocked_thread_info is None:
                                blocked_thread_info = {'sqls': []}
                                thread_transactions[str(thread_id)] = blocked_thread_info
                            bt_has_tc = any(
                                any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit', 'innodb_lock_wait_timeout', 'lock_wait_timeout'])
                                for log in blocked_thread_info.get('sqls', [])
                            )
                            if not bt_has_tc:
                                bt_tc_start = int((problem_time - timedelta(minutes=10)).timestamp() * 1000)
                                bt_tc_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                                bt_tc_logs = self.query_transaction_controls({str(thread_id)}, bt_tc_start, bt_tc_end, max_pages=3)
                                if bt_tc_logs:
                                    existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in blocked_thread_info.get('sqls', []))
                                    for log in bt_tc_logs:
                                        if str(log.get('ThreadID', '')) == str(thread_id):
                                            key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                            if key not in existing_keys:
                                                blocked_thread_info['sqls'].append(log)
                                                existing_keys.add(key)
                                    blocked_thread_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                            
                            # Render blocking chain (transaction timeline format)
                            self._render_blocking_chain(root_source, chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info, blocked_sql_audit=target_blocked, lock_type='row' if lock_time > 10000 else 'mdl')
                    else:
                        # COMMIT-match fallback
                        print('  ℹ️  Time overlap analysis did not find lock holder, trying COMMIT-match...')
                        cm_root, cm_chain = self._commit_match_fallback(
                            table_name, blocked_sql, lock_ref_utc_str,
                            lock_time, problem_time, thread_id)
                        if cm_root:
                            root_source = cm_root
                            blocked_in_chain = cm_chain
                            root_tid, root_info = root_source
                            lock_source_threads = [root_tid]
                            blocked_thread_info = thread_transactions.get(str(thread_id))
                            if blocked_thread_info is None:
                                blocked_thread_info = {'sqls': []}
                                thread_transactions[str(thread_id)] = blocked_thread_info
                            self._render_blocking_chain(
                                root_source, cm_chain, thread_id, sql,
                                problem_time, problem_time_utc_str,
                                blocked_thread_info, blocked_sql_audit=target_blocked,
                                lock_type='row' if lock_time > 10000 else 'mdl')
                        else:
                            print('⚠️  Full table DML query also did not find lock holder')
                            print(f'   Problem time: {problem_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} (Beijing time)')
                            print()
                            print('   Possible reasons:')
                            print('   1. Lock holder transaction DML was executed >2 hours ago (long uncommitted transaction)')
                            print('   2. Lock holder is SQL on another table (foreign key relation etc.)')
                            print()

                            if fallback_blocked:
                                print('   Reference: same-table operations found after problem time:')
                                for tid, info in fallback_blocked:
                                    dml_sql = ''
                                    for log in info['sqls']:
                                        if any(kw in log.get('SQLText', '').lower() for kw in ['update', 'delete', 'insert', 'for update', 'lock in share mode']):
                                            dml_sql = log.get('SQLText', '')
                                            break
                                    print(f'     Thread {tid} | {self.utc_to_beijing(info["dml_time"])} | {dml_sql}')
                                print()
                else:
                    # No DML found on same table either, fallback to smart query
                    print('⚠️  Full table query found no DML either, falling back to smart query...')
                    print()
                    all_logs, batch_results = self.query_sql_logs_parallel(instance_id, problem_time)

        
        else:
            # No WHERE conditions (e.g. DDL, FLUSH): direct smart query
            print('=' * 120)
            print('Step 3: Smart query (7 concurrent batches)')
            print('=' * 120)
            print()
            
            all_logs, batch_results = self.query_sql_logs_parallel(instance_id, problem_time)
            
            # MDL lock analysis: targeted query for same-table DML, find uncommitted transaction threads
            # Conditions: 1) has table + MDL lock  2) no table but SQL is global MDL operation (e.g. FTWRL)
            blocked_sql_type = (sql or '').strip().split()[0].upper() if sql else ''
            is_global_mdl = not table_name and blocked_sql_type in ('FLUSH', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME', 'LOCK')
            if (table_name and lock_time <= 10000) or is_global_mdl:
                print('=' * 120)
                print('Step 4: MDL lock time overlap analysis')
                print('=' * 120)
                print()
                # MDL lock reference time = blocked SQL DAS OriginTime (when MDL lock wait started)
                # Cannot use problem_time_utc_str (user-provided timeout time), as that is post-timeout
                # Only threads still holding MDL lock when blocked SQL started are true blockers
                ddl_start_utc_str = blocked_sql.get('OriginTime', '')
                ddl_start_beijing = self.utc_to_beijing(ddl_start_utc_str)
                print(f'  Blocked SQL start time (UTC): {ddl_start_utc_str}')
                print(f'  Blocked SQL start time (Beijing): {ddl_start_beijing}')
                if is_global_mdl:
                    print(f'  MDL lock holder criteria: global MDL operation ({blocked_sql_type}), thread with uncommitted transaction or long query on any table when blocked SQL started')
                else:
                    print(f'  MDL lock holder criteria: thread on {table_name}  with uncommitted transaction or long SELECT when blocked SQL started (holds MDL lock)')
                print()
                
                if is_global_mdl:
                    # Global MDL operation (e.g. FTWRL): cannot query by table
                    # Step 3 batches do not include plain SELECT, need extra long SELECT query
                    table_dml_logs = batch_results.get('DML operations (UPDATE/DELETE/INSERT)', [])
                    table_select_logs = []  # Global operation cannot filter SELECT by table
                    flush_logs = batch_results.get('FLUSH operations', [])
                    lock_table_logs = batch_results.get('Lock operations (LOCK/UNLOCK)', [])

                    # Query long SELECT separately (plain SELECT not in 7 batches, but holds MDL SR lock)
                    mdl_long_select_start = int((problem_time - timedelta(hours=1)).timestamp() * 1000)
                    mdl_long_select_end = int((problem_time + timedelta(minutes=30)).timestamp() * 1000)
                    global_select_logs = self.query_sql_logs_by_keywords(
                        mdl_long_select_start, mdl_long_select_end, ['select'], max_pages=5
                    )
                    long_select_logs = [
                        log for log in global_select_logs
                        if (log.get('SQLText', '') or '').lower().strip().startswith('select')
                        and (log.get('Latancy', 0) or 0) >= 5000000
                    ]

                    print(f'  ✅ Using step 3 data: DML {len(table_dml_logs)}  , FLUSH {len(flush_logs)}  , LOCK TABLES {len(lock_table_logs)}  ')
                    print(f'  ✅ Extra long SELECT query (>= 5s): {len(long_select_logs)}  ')
                    print()
                else:
                    # Has table: concurrent query for five types of MDL lock holders
                    mdl_start_ms = int((problem_time - timedelta(hours=1)).timestamp() * 1000)
                    mdl_end_ms = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                    mdl_long_select_end_ms = int((problem_time + timedelta(minutes=30)).timestamp() * 1000)

                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        future_dml = executor.submit(
                            self.query_sql_logs_by_where_condition,
                            table_name, None, mdl_start_ms, mdl_end_ms, 10
                        )
                        future_long_select = executor.submit(
                            self.query_long_running_selects,
                            table_name, mdl_start_ms, mdl_long_select_end_ms, 5000000, 5
                            # Threshold 5s (not 60s): killed long SELECT (e.g. SELECT SLEEP(600)) actual Latancy may be much less than expected
                        )
                        future_table_select = executor.submit(
                            self.query_table_selects,
                            table_name, mdl_start_ms, mdl_end_ms, 5
                        )
                        future_flush = executor.submit(
                            self.query_sql_logs_by_keywords,
                            mdl_start_ms, mdl_end_ms, ['flush']
                        )
                        future_lock_table = executor.submit(
                            self.query_sql_logs_by_keywords,
                            mdl_start_ms, mdl_end_ms, ['lock tables']
                        )
                        table_dml_logs = future_dml.result()
                        long_select_logs = future_long_select.result()
                        table_select_logs = future_table_select.result()
                        flush_logs = future_flush.result()
                        lock_table_logs = future_lock_table.result()
                
                # Deduplicate DML
                seen_keys = set()
                deduped_table_dml = []
                for log in table_dml_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_table_dml.append(log)
                table_dml_logs = deduped_table_dml
                                
                # Deduplicate long SELECT
                deduped_select = []
                for log in long_select_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_select.append(log)
                long_select_logs = deduped_select
                
                # Deduplicate in-transaction SELECT
                deduped_table_select = []
                for log in table_select_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_table_select.append(log)
                table_select_logs = deduped_table_select
                
                # Deduplicate FLUSH
                deduped_flush = []
                for log in flush_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_flush.append(log)
                flush_logs = deduped_flush

                # Deduplicate LOCK TABLES
                deduped_lock_table = []
                for log in lock_table_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_lock_table.append(log)
                lock_table_logs = deduped_lock_table

                print(f'  ✅ Same-table DML query found {len(table_dml_logs)}  (deduplicated)')
                print(f'  ✅ Same-table long SELECT (>= 5s) found {len(long_select_logs)}  (deduplicated)')
                print(f'  ✅ Same-table in-transaction SELECT found {len(table_select_logs)}  (deduplicated)')
                print(f'  ✅ FLUSH operations found {len(flush_logs)}  (deduplicated)')
                print(f'  ✅ LOCK TABLES operations found {len(lock_table_logs)}  (deduplicated)')
                print()

                # Merge DML + long SELECT + in-transaction SELECT + FLUSH + LOCK TABLES
                mdl_candidate_logs = table_dml_logs + long_select_logs + table_select_logs + flush_logs + lock_table_logs
                
                # Supplement transaction control statements
                related_thread_ids = set(str(log.get('ThreadID')) for log in mdl_candidate_logs)
                related_thread_ids.add(str(thread_id))
                tc_start = int((problem_time - timedelta(hours=1)).timestamp() * 1000)
                tc_end = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                tc_logs = self.query_transaction_controls(related_thread_ids, tc_start, tc_end, max_pages=5)
                
                # Deduplicate TC logs
                seen_tc = set()
                deduped_tc = []
                for log in tc_logs:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_tc:
                        seen_tc.add(key)
                        deduped_tc.append(log)
                tc_logs = deduped_tc
                
                # Merge and analyze transaction state
                all_thread_logs = mdl_candidate_logs + tc_logs
                thread_transactions = {}
                for log in sorted(all_thread_logs, key=lambda x: x.get('OriginTime', '')):
                    tid = str(log.get('ThreadID', ''))
                    sql_text_l = (log.get('SQLText', '') or '').lower()
                    transaction_id = log.get('TransactionId', '')
                    origin_time = log.get('OriginTime', '')
                    
                    if tid not in thread_transactions:
                        thread_transactions[tid] = {
                            'started': False, 'has_dml': False,
                            'has_long_select': False, 'has_select': False,
                            'has_flush': False, 'has_lock_table': False,
                            'dml_time': None, 'commit_time': None,
                            'select_start': None, 'select_end': None,
                            'select_time': None,
                            'flush_time': None, 'flush_end': None,
                            'lock_table_time': None, 'lock_table_end': None,
                            'lock_time': 0, 'sqls': [],
                            'transaction_id': transaction_id,
                            '_logout_end_time': None
                        }
                    
                    # Session boundary: SQL after logout belongs to new session, reset transaction state
                    # Consecutive logout records are same disconnect (DAS may return duplicates), no reset
                    logout_end = thread_transactions[tid].get('_logout_end_time')
                    if logout_end and origin_time > logout_end and 'logout' not in sql_text_l:
                        thread_transactions[tid]['started'] = False
                        thread_transactions[tid]['has_dml'] = False
                        thread_transactions[tid]['has_long_select'] = False
                        thread_transactions[tid]['has_select'] = False
                        thread_transactions[tid]['has_flush'] = False
                        thread_transactions[tid]['has_lock_table'] = False
                        thread_transactions[tid]['dml_time'] = None
                        thread_transactions[tid]['commit_time'] = None
                        thread_transactions[tid]['select_start'] = None
                        thread_transactions[tid]['select_end'] = None
                        thread_transactions[tid]['select_time'] = None
                        thread_transactions[tid]['flush_time'] = None
                        thread_transactions[tid]['flush_end'] = None
                        thread_transactions[tid]['lock_table_time'] = None
                        thread_transactions[tid]['lock_table_end'] = None
                        thread_transactions[tid]['lock_time'] = 0
                        thread_transactions[tid]['_logout_end_time'] = None
                        thread_transactions[tid]['transaction_id'] = transaction_id
                    
                    thread_transactions[tid]['sqls'].append(log)
                    
                    if any(kw in sql_text_l for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                        thread_transactions[tid]['started'] = True
                        thread_transactions[tid]['has_dml'] = False
                        thread_transactions[tid]['has_long_select'] = False
                        thread_transactions[tid]['has_select'] = False
                        thread_transactions[tid]['has_flush'] = False
                        thread_transactions[tid]['has_lock_table'] = False
                        thread_transactions[tid]['dml_time'] = None
                        thread_transactions[tid]['commit_time'] = None
                        thread_transactions[tid]['select_start'] = None
                        thread_transactions[tid]['select_end'] = None
                        thread_transactions[tid]['select_time'] = None
                        thread_transactions[tid]['flush_time'] = None
                        thread_transactions[tid]['flush_end'] = None
                        thread_transactions[tid]['lock_table_time'] = None
                        thread_transactions[tid]['lock_table_end'] = None
                        thread_transactions[tid]['lock_time'] = 0

                    if any(kw in sql_text_l for kw in ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']):
                        thread_transactions[tid]['has_dml'] = True
                        if not thread_transactions[tid]['dml_time']:
                            thread_transactions[tid]['dml_time'] = origin_time
                            thread_transactions[tid]['lock_time'] = log.get('LockTime', 0) or 0

                    # Long SELECT: calculate end time via OriginTime + Latancy
                    # Threshold 5s: killed long SELECT (e.g. SELECT SLEEP(600)) actual Latancy may only be a few seconds
                    if sql_text_l.strip().startswith('select'):
                        latency_us = log.get('Latancy', 0) or 0
                        if latency_us >= 5000000:  # >= 5 s
                            thread_transactions[tid]['has_long_select'] = True
                            thread_transactions[tid]['select_start'] = origin_time
                            # Calculate SELECT end time = start time + execution latency
                            try:
                                start_dt = datetime.strptime(origin_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                                end_dt = start_dt + timedelta(microseconds=latency_us)
                                thread_transactions[tid]['select_end'] = end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                            except Exception:
                                pass
                        # In-transaction plain SELECT: if thread has open transaction, plain SELECT also holds MDL lock
                        if 'for update' not in sql_text_l and 'lock in share mode' not in sql_text_l:
                            thread_transactions[tid]['has_select'] = True
                            if not thread_transactions[tid]['select_time']:
                                thread_transactions[tid]['select_time'] = origin_time

                    # FLUSH operation: needs exclusive MDL lock, intermediate in MDL blocking chain
                    if 'flush' in sql_text_l:
                        thread_transactions[tid]['has_flush'] = True
                        if not thread_transactions[tid].get('flush_time'):
                            thread_transactions[tid]['flush_time'] = origin_time
                            latency_us = log.get('Latancy', 0) or 0
                            if latency_us > 0:
                                try:
                                    start_dt = datetime.strptime(origin_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                                    end_dt = start_dt + timedelta(microseconds=latency_us)
                                    thread_transactions[tid]['flush_end'] = end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                                except Exception:
                                    pass

                    # LOCK TABLES: holds table exclusive lock (MDL_SHARED_NO_READ_WRITE), until UNLOCK TABLES or session disconnect
                    if 'lock tables' in sql_text_l and 'unlock' not in sql_text_l:
                        thread_transactions[tid]['has_lock_table'] = True
                        if not thread_transactions[tid].get('lock_table_time'):
                            thread_transactions[tid]['lock_table_time'] = origin_time
                            latency_us = log.get('Latancy', 0) or 0
                            if latency_us > 0:
                                try:
                                    start_dt = datetime.strptime(origin_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                                    end_dt = start_dt + timedelta(microseconds=latency_us)
                                    thread_transactions[tid]['lock_table_end'] = end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                                except Exception:
                                    pass

                    # UNLOCK TABLES: release LOCK TABLES held lock
                    if 'unlock tables' in sql_text_l:
                        if not thread_transactions[tid]['commit_time']:
                            thread_transactions[tid]['commit_time'] = origin_time

                    if any(kw in sql_text_l for kw in ['commit', 'rollback']) and 'autocommit' not in sql_text_l:
                        if not thread_transactions[tid]['commit_time']:
                            thread_transactions[tid]['commit_time'] = origin_time
                    
                    # logout! means session disconnect, MySQL auto-rolls back uncommitted transactions
                    if 'logout' in sql_text_l:
                        latency_us = log.get('Latancy', 0) or 0
                        logout_end_time = self._calc_logout_end_time(origin_time, latency_us)
                        if not thread_transactions[tid]['commit_time']:
                            thread_transactions[tid]['commit_time'] = logout_end_time
                        thread_transactions[tid]['_logout_end_time'] = logout_end_time
                
                # MDL lock holder determination:
                # 1) DML in uncommitted transaction (transaction spans blocked SQL start time)
                # 2) Long SELECT (execution spans blocked SQL start time)
                # 3) In-transaction plain SELECT (transaction spans blocked SQL start time)
                # 4) FLUSH operation (execution spans blocked SQL start time, needs exclusive MDL lock)
                # 5) LOCK TABLES (holds table exclusive lock, until UNLOCK TABLES or session disconnect)
                mdl_holders = []

                for tid, info in thread_transactions.items():
                    if tid == str(thread_id):
                        continue
                    if os.environ.get('LOCK_DBG'):
                        print('  [DBG-T] tid=' + str(tid) + ' has_flush=' + str(info.get('has_flush')) + ' flush_time=' + str(info.get('flush_time')) + ' flush_end=' + str(info.get('flush_end')) + ' has_lock_table=' + str(info.get('has_lock_table')) + ' lock_table_time=' + str(info.get('lock_table_time')), flush=True)

                    is_mdl_holder = False
                    holder_time = None
                    holder_reason = None
                    
                    # Case 1: DML in uncommitted transaction (spans blocked SQL start)
                    if info['has_dml']:
                        dml_time = info['dml_time']
                        commit_time = info['commit_time']
                        if dml_time and dml_time < ddl_start_utc_str:
                            if commit_time is None or commit_time > ddl_start_utc_str:
                                is_mdl_holder = True
                                holder_time = dml_time
                                holder_reason = 'dml'
                    
                    # Case 2: Long SELECT (execution spans blocked SQL start)
                    if not is_mdl_holder and info['has_long_select']:
                        select_start = info['select_start']
                        select_end = info['select_end']
                        if select_start and select_start < ddl_start_utc_str:
                            if select_end is None or select_end > ddl_start_utc_str:
                                is_mdl_holder = True
                                holder_time = select_start
                                holder_reason = 'long_select'
                                if not info['dml_time']:
                                    info['dml_time'] = select_start
                    
                    # Case 3: In-transaction plain SELECT (transaction spans blocked SQL start)
                    if not is_mdl_holder and info['has_select'] and info['started']:
                        select_time = info['select_time']
                        commit_time = info['commit_time']
                        if select_time and select_time < ddl_start_utc_str:
                            if commit_time is None or commit_time > ddl_start_utc_str:
                                is_mdl_holder = True
                                holder_time = select_time
                                holder_reason = 'txn_select'
                                if not info['dml_time']:
                                    info['dml_time'] = select_time
                    
                    # Case 4: FLUSH operation (execution spans blocked SQL start)
                    # FLUSH TABLE needs exclusive MDL lock, intermediate in blocking chain
                    # Relaxed boundary: FLUSH ending after problem time (occupied MDL in wait window) counts as intermediate blocker
                    if not is_mdl_holder and info.get('has_flush'):
                        flush_time = info.get('flush_time')
                        flush_end = info.get('flush_end')
                        ref_time = problem_time_utc_str if problem_time_utc_str < ddl_start_utc_str else ddl_start_utc_str
                        if os.environ.get('LOCK_DBG'):
                            print(f'  [DBG-FLUSH] tid={tid} flush_time={flush_time} flush_end={flush_end} ref_time={ref_time} ddl_start={ddl_start_utc_str}', flush=True)
                        if flush_time and flush_time < ddl_start_utc_str:
                            if flush_end is None or flush_end > ref_time:
                                is_mdl_holder = True
                                holder_time = flush_time
                                holder_reason = 'flush'
                                if not info['dml_time']:
                                    info['dml_time'] = flush_time

                    # Case 5: LOCK TABLES (holds MDL_SHARED_NO_READ_WRITE, until UNLOCK TABLES or session disconnect)
                    if not is_mdl_holder and info.get('has_lock_table'):
                        lt_time = info.get('lock_table_time')
                        commit_time = info['commit_time']
                        if lt_time and lt_time < ddl_start_utc_str:
                            if commit_time is None or commit_time > ddl_start_utc_str:
                                is_mdl_holder = True
                                holder_time = lt_time
                                holder_reason = 'lock_table'
                                if not info['dml_time']:
                                    info['dml_time'] = lt_time

                    if is_mdl_holder:
                        mdl_holders.append((tid, info, holder_time, holder_reason))
                
                print(f'  ℹ️  Initially filtered {len(mdl_holders)}  MDL holder candidates, starting TC query verification...')
                
                # Supplement TC query for all MDL holder candidates to ensure commit_time accuracy
                tc_query_start = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                tc_query_end = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                
                for cand_tid, cand_info, _, _ in mdl_holders:
                    if cand_info['commit_time'] is not None:
                        continue  # commit_time known, no supplement needed
                    # Query TC specifically for candidates with unknown commit_time
                    cand_tc_logs = self.query_transaction_controls({cand_tid}, tc_query_start, tc_query_end, max_pages=3)
                    existing_keys = set((str(l.get('ThreadID','')), l.get('OriginTime',''), l.get('SQLText','')) for l in cand_info['sqls'])
                    for log in cand_tc_logs:
                        if str(log.get('ThreadID', '')) == cand_tid:
                            key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                            if key not in existing_keys:
                                cand_info['sqls'].append(log)
                                existing_keys.add(key)
                                sql_lower_c = log.get('SQLText', '').lower()
                                if any(kw in sql_lower_c for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                                    cand_info['started'] = True
                                if any(kw in sql_lower_c for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower_c:
                                    if not cand_info['commit_time']:
                                        cand_info['commit_time'] = log.get('OriginTime', '')
                                # logout! = Session disconnected, transaction auto-rolled back
                                if 'logout' in sql_lower_c:
                                    if not cand_info['commit_time']:
                                        latency_us = log.get('Latancy', 0) or 0
                                        cand_info['commit_time'] = self._calc_logout_end_time(log.get('OriginTime', ''), latency_us)
                    cand_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                
                # Re-filter valid MDL holders with verified commit_time
                root_source = None
                blocked_in_chain = []
                
                # Pass 1: Non-FLUSH MDL holders (true lock holders: DML/long SELECT/in-txn SELECT), select root cause
                # Sort priority:
                #   1. Candidates with lock_time <= 10000 first (not blocked by row lock = true root cause)
                #   2. Candidates with lock_time > 10000 next (waiting for row lock = intermediate, not root cause)
                #   3. Within same group, sort by holder_time ASC (earliest DML most likely root cause)
                for tid, info, holder_time, holder_reason in sorted(
                    [h for h in mdl_holders if h[3] != 'flush'],
                    key=lambda x: (x[1]['lock_time'] > 10000, x[2] or '')
                ):
                    # Case 2 (long SELECT): MDL lock held during SELECT execution, not transaction-dependent
                    # Use select_end, not commit_time (commit_time may be from previous session logout)
                    if holder_reason == 'long_select':
                        select_end = info.get('select_end')
                        if select_end is not None and select_end <= ddl_start_utc_str:
                            print(f'  ⚠️  Candidate thread {tid} long SELECT ended at {self.utc_to_beijing(select_end)}  (before blocked SQL start {ddl_start_beijing}), excluding')
                            continue
                    else:
                        # Case 1/3: Transaction-based MDL hold, use commit_time
                        commit_time = info['commit_time']
                        if commit_time is not None and commit_time <= ddl_start_utc_str:
                            print(f'  ⚠️  Candidate thread {tid} transaction committed at {self.utc_to_beijing(commit_time)}  (before blocked SQL start {ddl_start_beijing}), excluding')
                            continue
                    
                    # Valid MDL holder
                    if root_source is None:
                        root_source = (tid, info)
                    else:
                        blocked_in_chain.append((tid, info))
                
                # Pass 2: FLUSH operations (intermediate blockers: block subsequent requests while waiting for exclusive MDL), as chain members
                for tid, info, holder_time, holder_reason in sorted(
                    [h for h in mdl_holders if h[3] == 'flush'],
                    key=lambda x: x[2] or ''
                ):
                    flush_end = info.get('flush_end')
                    flush_time = info.get('flush_time') or holder_time
                    # Only exclude FLUSH if it completed before blocked SQL start AND before user problem time
                    # Otherwise FLUSH is in wait window or released MDL right before blocked SQL, should be chain member
                    if flush_end is not None and flush_end <= problem_time_utc_str:
                        print(f'  ⚠️  Candidate thread {tid} FLUSH completed at {self.utc_to_beijing(flush_end)}  (before problem time {self.utc_to_beijing(problem_time_utc_str)}), excluding')
                        continue
                    blocked_in_chain.append((tid, info))
                
                if root_source:
                    root_tid, root_info = root_source
                    lock_source_threads = [root_tid]
                    print(f'  ✅ Confirmed lock holder thread: {root_tid}')
                    
                    # Get diagnosed thread transaction context
                    blocked_thread_info = thread_transactions.get(str(thread_id))
                    if blocked_thread_info is None:
                        blocked_thread_info = {'sqls': []}
                        thread_transactions[str(thread_id)] = blocked_thread_info
                    bt_has_tc = any(
                        any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit', 'innodb_lock_wait_timeout', 'lock_wait_timeout'])
                        for log in blocked_thread_info.get('sqls', [])
                    )
                    if not bt_has_tc:
                        bt_tc_start = int((problem_time - timedelta(minutes=10)).timestamp() * 1000)
                        bt_tc_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                        bt_tc_logs = self.query_transaction_controls({str(thread_id)}, bt_tc_start, bt_tc_end, max_pages=3)
                        if bt_tc_logs:
                            existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in blocked_thread_info.get('sqls', []))
                            for log in bt_tc_logs:
                                if str(log.get('ThreadID', '')) == str(thread_id):
                                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                    if key not in existing_keys:
                                        blocked_thread_info['sqls'].append(log)
                                        existing_keys.add(key)
                            blocked_thread_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                    
                    # Filter intermediate blocked threads
                    chain_members = []
                    root_dml_time = root_info['dml_time']
                    for tid_c, info_c in blocked_in_chain:
                        chain_members.append((tid_c, info_c))
                    chain_members.sort(key=lambda x: x[1].get('dml_time', ''))
                    
                    # Render blocking chain
                    self._render_blocking_chain(root_source, chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info, blocked_sql_audit=target_blocked, lock_type='mdl')
                else:
                    print('  ⚠️  MDL lock holder not found in audit logs, auto-querying current sessions...')
                    print()
                    
                    # Fallback: call GetMySQLAllSessionAsync to check active sessions
                    try:
                        session_data = self.query_all_sessions()
                        if session_data:
                            total = session_data.get('TotalSessionCount', 0)
                            active = session_data.get('ActiveSessionCount', 0)
                            print(f'  ℹ️  Current sessions: total {total} , active {active} ')
                            
                            holder_session, holder_reason = self._find_mdl_holder_from_sessions(session_data, table_name, thread_id)
                            if holder_session:
                                holder_sid = holder_session.get('SessionId', '')
                                holder_sql = holder_session.get('SqlText', '') or ''
                                holder_user = holder_session.get('User', '')
                                holder_client = holder_session.get('Client', '')
                                holder_time = holder_session.get('Time', 0)
                                holder_trx = holder_session.get('TrxDuration', 0)
                                holder_command = holder_session.get('Command', '')
                                
                                print(f'  ✅ Found possible MDL lock holder via live session query:')
                                print(f'     Session ID: {holder_sid}')
                                print(f'     User: {holder_user}')
                                print(f'     Client: {holder_client}')
                                print(f'     Command: {holder_command}')
                                print(f'     Exec time: {holder_time}s')
                                print(f'     Trx duration: {holder_trx}s')
                                print(f'     SQL: {holder_sql[:200]}')
                                print(f'     Reason: {holder_reason}')
                                print()
                                
                                # Set as lock holder
                                lock_source_threads = [str(holder_sid)]
                                root_source = (str(holder_sid), {
                                    'started': True,
                                    'has_dml': True,
                                    'dml_time': None,
                                    'commit_time': None,
                                    'lock_time': 0,
                                    'sqls': [],
                                    'transaction_id': holder_session.get('TrxId', ''),
                                    'session_source': True,  # Marked as from session query
                                    'session_info': holder_session,
                                    'session_reason': holder_reason
                                })
                            else:
                                print('  ⚠️  No clear MDL lock holder found in current sessions either')
                                print()
                    except Exception as e:
                        print(f'  ⚠️  GetMySQLAllSessionAsync Query failed: {e}')
                        print()
            
            elif table_name and lock_time > 10000:
                # InnoDB row lock analysis (no WHERE conditions, e.g. INSERT): full table DML query
                print('=' * 120)
                print('Step 4: InnoDB row lock full table analysis (no WHERE conditions)')
                print('=' * 120)
                print()
                print(f'  Blocked SQL has no WHERE conditions (INSERT), falling back to full table DML query')
                print(f'  Lock holder may be transaction holding Gap Lock / Next-Key Lock')
                print()
                
                # Query all DML on same table - split into two windows to cover lock wait start time
                lock_time_sec = lock_time / 1000000.0
                lock_wait_start = problem_time - timedelta(seconds=lock_time_sec)

                # Window 1: Near lock wait start time (most likely position for lock holder DML)
                lws_start = int((lock_wait_start - timedelta(minutes=5)).timestamp() * 1000)
                lws_end = int((lock_wait_start + timedelta(seconds=30)).timestamp() * 1000)
                print(f'  📍 Lock wait start time: {lock_wait_start.strftime("%H:%M:%S.%f")[:-3]}（LockTime={lock_time_sec:.3f}s）')
                table_all_sqls = self.query_sql_logs_by_where_condition(
                    table_name, None, lws_start, lws_end, max_pages=10
                )
                print(f'  Window 1 [lock wait start +/-5min]: {len(table_all_sqls)}  ')

                # Window 2: Near problem time (blocked thread and concurrent blocked threads)
                pt_start = int((problem_time - timedelta(minutes=2)).timestamp() * 1000)
                pt_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                table_sqls_pt = self.query_sql_logs_by_where_condition(
                    table_name, None, pt_start, pt_end, max_pages=5
                )
                print(f'  Window 2 [problem time +/-few min]: {len(table_sqls_pt)}  ')
                table_all_sqls.extend(table_sqls_pt)

                # Window 3: If window 1 insufficient, expand to -30min
                if len(table_all_sqls) < 5:
                    start_ms_wide = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                    end_ms_wide = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                    table_sqls_wide = self.query_sql_logs_by_where_condition(
                        table_name, None, start_ms_wide, end_ms_wide, max_pages=10
                    )
                    print(f'  Window 3 [expanded -30min]: {len(table_sqls_wide)}  ')
                    table_all_sqls.extend(table_sqls_wide)

                # Deduplicate
                seen_keys = set()
                deduped_table_sqls = []
                for log in table_all_sqls:
                    key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduped_table_sqls.append(log)
                table_all_sqls = deduped_table_sqls

                print(f'  ✅ Full table DML found {len(table_all_sqls)}  (deduplicated)')
                print()
                
                if table_all_sqls:
                    all_logs = table_all_sqls
                    batch_results['full_table_DML'] = table_all_sqls
                    
                    # Collect thread transaction control
                    related_thread_ids = set(str(log.get('ThreadID')) for log in table_all_sqls)
                    related_thread_ids.add(str(thread_id))

                    # When INSERT blocked, additionally find SERIALIZABLE threads (plain SELECT also holds lock)
                    tc_start = int((problem_time - timedelta(hours=2)).timestamp() * 1000)
                    tc_end = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                    try:
                        ser_tids = self.query_serializable_threads(tc_start, tc_end)
                        new_ser = ser_tids - related_thread_ids
                        if new_ser:
                            print(f'  🔍 Found {len(new_ser)}  SERIALIZABLE Thread: {", ".join(sorted(new_ser))}')
                            related_thread_ids.update(new_ser)
                    except NotImplementedError:
                        pass

                    tc_logs = self.query_transaction_controls(related_thread_ids, tc_start, tc_end)
                    
                    seen_tc = set()
                    deduped_tc = []
                    for log in tc_logs:
                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                        if key not in seen_tc:
                            seen_tc.add(key)
                            deduped_tc.append(log)
                    tc_logs = deduped_tc
                    
                    # Merge analysis
                    all_thread_logs = table_all_sqls + tc_logs
                    thread_transactions = {}
                    for log in sorted(all_thread_logs, key=lambda x: x.get('OriginTime', '')):
                        tid = str(log.get('ThreadID', ''))
                        sql_text_l = (log.get('SQLText', '') or '').lower()
                        transaction_id = log.get('TransactionId', '')
                        origin_time = log.get('OriginTime', '')
                        
                        if tid not in thread_transactions:
                            thread_transactions[tid] = {
                                'started': False, 'has_dml': False,
                                'has_lock_table': False,
                                '_is_serializable': False,
                                'dml_time': None, 'commit_time': None,
                                'lock_time': 0, 'sqls': [],
                                'transaction_id': transaction_id,
                                '_logout_end_time': None
                            }

                        # Session boundary detection: consecutive logout is same disconnect, no reset
                        logout_end = thread_transactions[tid].get('_logout_end_time')
                        if logout_end and origin_time > logout_end and 'logout' not in sql_text_l:
                            thread_transactions[tid]['started'] = False
                            thread_transactions[tid]['has_dml'] = False
                            thread_transactions[tid]['_is_serializable'] = False
                            thread_transactions[tid]['dml_time'] = None
                            thread_transactions[tid]['commit_time'] = None
                            thread_transactions[tid]['lock_time'] = 0
                            thread_transactions[tid]['_logout_end_time'] = None
                            thread_transactions[tid]['transaction_id'] = transaction_id

                        thread_transactions[tid]['sqls'].append(log)

                        if any(kw in sql_text_l for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                            thread_transactions[tid]['started'] = True
                            thread_transactions[tid]['has_dml'] = False
                            thread_transactions[tid]['dml_time'] = None
                            thread_transactions[tid]['commit_time'] = None
                            thread_transactions[tid]['lock_time'] = 0

                        if any(kw in sql_text_l for kw in ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']):
                            thread_transactions[tid]['has_dml'] = True
                            if not thread_transactions[tid]['dml_time']:
                                thread_transactions[tid]['dml_time'] = origin_time
                                thread_transactions[tid]['lock_time'] = log.get('LockTime', 0) or 0

                        # SERIALIZABLE detection
                        if ('set' in sql_text_l
                                and ('transaction_isolation' in sql_text_l or 'tx_isolation' in sql_text_l
                                     or 'transaction isolation' in sql_text_l)
                                and 'serializable' in sql_text_l):
                            thread_transactions[tid]['_is_serializable'] = True

                        if any(kw in sql_text_l for kw in ['commit', 'rollback']) and 'autocommit' not in sql_text_l:
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = origin_time

                        if 'lock tables' in sql_text_l and 'unlock' not in sql_text_l:
                            thread_transactions[tid]['has_lock_table'] = True
                            if not thread_transactions[tid]['dml_time']:
                                thread_transactions[tid]['dml_time'] = origin_time

                        if 'unlock tables' in sql_text_l:
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = origin_time

                        if 'logout' in sql_text_l:
                            latency_us = log.get('Latancy', 0) or 0
                            logout_end_time = self._calc_logout_end_time(origin_time, latency_us)
                            if not thread_transactions[tid]['commit_time']:
                                thread_transactions[tid]['commit_time'] = logout_end_time
                            thread_transactions[tid]['_logout_end_time'] = logout_end_time

                    # SERIALIZABLE supplement: query SELECT to set dml_time
                    for tid, info in thread_transactions.items():
                        if info.get('_is_serializable') and not info['has_dml'] and tid != str(thread_id):
                            sel_start = int((problem_time - timedelta(hours=2)).timestamp() * 1000)
                            sel_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                            thread_selects = self.query_thread_select_on_table(
                                tid, table_name, sel_start, sel_end, max_pages=3)
                            if thread_selects:
                                thread_selects.sort(key=lambda x: x.get('OriginTime', ''))
                                info['has_dml'] = True
                                info['_serializable'] = True
                                info['dml_time'] = thread_selects[0].get('OriginTime', '')
                                info['lock_time'] = thread_selects[0].get('LockTime', 0) or 0
                                existing_keys = set(
                                    (str(l.get('ThreadID', '')), l.get('OriginTime', ''), l.get('SQLText', ''))
                                    for l in info['sqls'])
                                for sel_log in thread_selects:
                                    key = (str(sel_log.get('ThreadID', '')), sel_log.get('OriginTime', ''), sel_log.get('SQLText', ''))
                                    if key not in existing_keys:
                                        info['sqls'].append(sel_log)
                                        existing_keys.add(key)
                                info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                                print(f'  ✅ Thread {tid} uses SERIALIZABLE,on {table_name}: {len(thread_selects)} SELECT (shared Next-Key Lock)')

                    # Time overlap analysis
                    LOCK_TIME_THRESHOLD = 100000
                    fallback_root = None
                    fallback_blocked = []

                    # Lock wait start time (UTC), for sort priority
                    try:
                        _ref_dt = datetime.strptime(lock_ref_utc_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                        _lws_dt = _ref_dt - timedelta(seconds=lock_time / 1000000.0)
                        lock_wait_start_utc_str = _lws_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    except Exception:
                        lock_wait_start_utc_str = lock_ref_utc_str

                    if os.environ.get('LOCK_DBG'):
                        print(f'  [DBG] lock_ref_utc_str = {lock_ref_utc_str}', flush=True)
                        print(f'  [DBG] lock_wait_start_utc_str = {lock_wait_start_utc_str}', flush=True)
                        for _tid, _info in thread_transactions.items():
                            print(f'  [DBG] thread {_tid}: has_dml={_info["has_dml"]} dml_time={_info["dml_time"]} commit_time={_info["commit_time"]} lock_time={_info["lock_time"]} sql_count={len(_info["sqls"])}', flush=True)

                    for tid, info in thread_transactions.items():
                        if not info['has_dml'] and not info.get('has_lock_table'):
                            continue
                        if tid == str(thread_id):
                            continue

                        dml_time = info['dml_time']
                        commit_time = info['commit_time']
                        lock_time_val = info['lock_time']

                        if dml_time and dml_time < lock_ref_utc_str:
                            if (commit_time is None or commit_time > lock_ref_utc_str):
                                if lock_time_val < LOCK_TIME_THRESHOLD:
                                    if fallback_root is None:
                                        fallback_root = (tid, info)
                                    else:
                                        cur_before = fallback_root[1]['dml_time'] <= lock_wait_start_utc_str
                                        new_before = dml_time <= lock_wait_start_utc_str
                                        if new_before and not cur_before:
                                            fallback_root = (tid, info)
                                        elif new_before == cur_before and dml_time > fallback_root[1]['dml_time']:
                                            fallback_root = (tid, info)
                                else:
                                    fallback_blocked.append((tid, info))
                            elif dml_time >= lock_ref_utc_str:
                                fallback_blocked.append((tid, info))
                    
                    # If candidate dml_time is after lock wait start, try COMMIT-match first
                    if fallback_root and fallback_root[1]['dml_time'] > lock_wait_start_utc_str:
                        blocked_state = str(blocked_sql.get('State', '') or '0')
                        if blocked_state in ('0', '', '1205'):
                            print(f'  ℹ️  Candidate lock holder DML is after lock wait start, trying COMMIT-match first...')
                            cm_root, cm_chain = self._commit_match_fallback(
                                table_name, blocked_sql, lock_ref_utc_str,
                                lock_time, problem_time, thread_id)
                            if cm_root:
                                fallback_root = cm_root
                                fallback_blocked = cm_chain

                    if fallback_root:
                        root_source = fallback_root
                        blocked_in_chain = fallback_blocked
                        root_tid, root_info = root_source
                        lock_source_threads = [root_tid]

                        # Supplement lock holder thread TC
                        has_tc = any(
                            any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit', 'commit', 'rollback'])
                            for log in root_info['sqls']
                        )
                        if not has_tc:
                            tc_start_root = int((problem_time - timedelta(minutes=30)).timestamp() * 1000)
                            tc_end_root = int((problem_time + timedelta(minutes=10)).timestamp() * 1000)
                            root_tc_logs = self.query_transaction_controls({root_tid}, tc_start_root, tc_end_root, max_pages=5)
                            if root_tc_logs:
                                existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in root_info['sqls'])
                                for log in root_tc_logs:
                                    if str(log.get('ThreadID', '')) == root_tid:
                                        key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                        if key not in existing_keys:
                                            root_info['sqls'].append(log)
                                            existing_keys.add(key)
                                            sql_lower = log.get('SQLText', '').lower()
                                            if any(kw in sql_lower for kw in ['begin', 'start transaction', 'set autocommit=0', 'set @@session.autocommit']):
                                                root_info['started'] = True
                                            if any(kw in sql_lower for kw in ['commit', 'rollback']) and 'autocommit' not in sql_lower:
                                                if not root_info['commit_time']:
                                                    root_info['commit_time'] = log.get('OriginTime', '')
                                root_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))

                        # Re-validate
                        if root_info['commit_time'] and root_info['commit_time'] <= lock_ref_utc_str:
                            root_source = None
                            lock_source_threads = []

                        if root_source:
                            print(f'  ✅ Confirmed lock holder thread: {root_tid}')
                            print()
                            
                            # Filter intermediate blocked threads
                            chain_members = []
                            root_dml_time = root_info['dml_time']
                            for tid_c, info_c in fallback_blocked:
                                dml_time_c = info_c.get('dml_time', '')
                                lock_time_c = info_c.get('lock_time', 0)
                                if dml_time_c and root_dml_time < dml_time_c < lock_ref_utc_str and lock_time_c >= 100000:
                                    chain_members.append((tid_c, info_c))
                            chain_members.sort(key=lambda x: x[1].get('dml_time', ''))
                            
                            # Diagnosed thread transaction context
                            blocked_thread_info = thread_transactions.get(str(thread_id))
                            if blocked_thread_info is None:
                                blocked_thread_info = {'sqls': []}
                                thread_transactions[str(thread_id)] = blocked_thread_info
                            bt_has_tc = any(
                                any(kw in log.get('SQLText', '').lower() for kw in ['begin', 'start transaction', 'set autocommit', 'innodb_lock_wait_timeout', 'lock_wait_timeout'])
                                for log in blocked_thread_info.get('sqls', [])
                            )
                            if not bt_has_tc:
                                bt_tc_start = int((problem_time - timedelta(minutes=10)).timestamp() * 1000)
                                bt_tc_end = int((problem_time + timedelta(minutes=5)).timestamp() * 1000)
                                bt_tc_logs = self.query_transaction_controls({str(thread_id)}, bt_tc_start, bt_tc_end, max_pages=3)
                                if bt_tc_logs:
                                    existing_keys = set((str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', '')) for log in blocked_thread_info.get('sqls', []))
                                    for log in bt_tc_logs:
                                        if str(log.get('ThreadID', '')) == str(thread_id):
                                            key = (str(log.get('ThreadID', '')), log.get('OriginTime', ''), log.get('SQLText', ''))
                                            if key not in existing_keys:
                                                blocked_thread_info['sqls'].append(log)
                                                existing_keys.add(key)
                                    blocked_thread_info['sqls'].sort(key=lambda x: x.get('OriginTime', ''))
                            
                            # Render blocking chain
                            self._render_blocking_chain(root_source, chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info, blocked_sql_audit=target_blocked, lock_type='row')
                    else:
                        # COMMIT-match fallback
                        print('  ℹ️  Time overlap analysis did not find lock holder, trying COMMIT-match...')
                        cm_root, cm_chain = self._commit_match_fallback(
                            table_name, blocked_sql, lock_ref_utc_str,
                            lock_time, problem_time, thread_id)
                        if cm_root:
                            root_source = cm_root
                            blocked_in_chain = cm_chain
                            root_tid, root_info = root_source
                            lock_source_threads = [root_tid]
                            blocked_thread_info = thread_transactions.get(str(thread_id))
                            if blocked_thread_info is None:
                                blocked_thread_info = {'sqls': []}
                                thread_transactions[str(thread_id)] = blocked_thread_info
                            self._render_blocking_chain(
                                root_source, cm_chain, thread_id, sql,
                                problem_time, problem_time_utc_str,
                                blocked_thread_info, blocked_sql_audit=target_blocked,
                                lock_type='row')
                        else:
                            print('  ⚠️  Full table DML query did not find lock holder')
                            print()

        # Step 5: Display full SQL timeline
        print('=' * 120)
        print('Step 5: Full SQL timeline')
        print('=' * 120)
        print()
        
        if not all_logs:
            print('❌ No related SQL logs found')
            return
        
        # Deduplicate (based on OriginTime + ThreadID + SQLText)
        unique_logs = {}
        for log in all_logs:
            key = (log.get('OriginTime'), log.get('ThreadID'), log.get('SQLText'))
            unique_logs[key] = log
        all_logs_sorted = sorted(unique_logs.values(), key=lambda x: x.get('OriginTime', ''))
        
        print(f'Total: {len(all_logs_sorted)}   SQL')
        print()
        
        for log in all_logs_sorted:
            beijing_time = self.utc_to_beijing(log.get('OriginTime', ''))
            sql_text = log.get('SQLText', '')
            tid = log.get('ThreadID', '')
            state = log.get('State', '')
            lock_time_val = log.get('LockTime', 0)
            lock_time_sec = lock_time_val / 1000000 if lock_time_val else 0
            transaction_id = log.get('TransactionId', '')
            
            state_desc = ''
            if state == '1205':
                state_desc = '(timeout)'
            elif state == '1213':
                state_desc = '(deadlock)'
            elif state == '1317':
                state_desc = '(KILL)'
            elif state in ['0', '']:
                state_desc = '(success)'
            
            print(f'{beijing_time} | Thread {tid:8} | {state_desc:6} | LockTime: {lock_time_sec:8.3f}s | TrxId: {transaction_id}')
            print(f'  SQL: {sql_text}')
            print()
        
        # Step 6: Diagnosis conclusion
        print('=' * 120)
        print('Step 6: Diagnosis conclusion')
        print('=' * 120)
        print()
        
        elapsed = _time.time() - diag_start
        print(f'⏱️  Diagnosis time: {elapsed:.3f} s')
        print()
        
        print('📋 Diagnosis summary:')
        print(f'   1. Blocked SQL executed at {self.utc_to_beijing(blocked_sql.get("OriginTime", ""))}  ')
        # Detect FLUSH operations in wait window (supplement for Flush Lock determination)
        try:
            _has_flush_in_window = False
            _wait_start = problem_time_utc_str
            _wait_end = blocked_sql.get('OriginTime', '') or problem_time_utc_str
            if _wait_end < _wait_start:
                _wait_start, _wait_end = _wait_end, _wait_start
            # Allow FLUSH within +/-5s (considering OriginTime may differ from commit time)
            from datetime import datetime as _dt2, timedelta as _td2
            try:
                _ws_dt = _dt2.strptime(_wait_start.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f') - _td2(seconds=5)
                _we_dt = _dt2.strptime(_wait_end.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f') + _td2(seconds=5)
                _ws_str = _ws_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                _we_str = _we_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            except Exception:
                _ws_str, _we_str = _wait_start, _wait_end
            for _t_info in (thread_transactions or {}).values():
                if _t_info.get('has_flush'):
                    _ft = _t_info.get('flush_time') or ''
                    if _ws_str <= _ft <= _we_str:
                        _has_flush_in_window = True
                        break
        except Exception:
            _has_flush_in_window = False
        lock_type_label = self._classify_lock_type_label(lock_time, root_source, sql, chain_members=blocked_in_chain)
        # If classified as MDL and FLUSH detected in window, adjust to Flush Lock
        if _has_flush_in_window and ('MDL' in lock_type_label or 'Metadata' in lock_type_label):
            # Detect FTWRL (global read lock)
            _has_ftwrl = False
            for _t_info in (thread_transactions or {}).values():
                for _s in _t_info.get('sqls', []):
                    if 'with read lock' in (_s.get('SQLText', '') or '').lower():
                        _has_ftwrl = True
                        break
                if _has_ftwrl:
                    break
            lock_type_label = 'Flush Lock + Global Read Lock' if _has_ftwrl else 'Flush Lock'
        print(f'   2. Lock type: {lock_type_label}')
        print(f'   3. Lock wait time: {lock_time / 1000000:.3f} s')
        print()
        
        if lock_source_threads:
            print('🔴 Lock holder identified:')
            print(f'   - Root cause thread: {lock_source_threads[0]}')
            print(f'   - This thread holds lock with uncommitted transaction, blocking subsequent threads')
            print()
            
            if root_source:
                root_tid_c, root_info_c = root_source
                
                # If lock holder from live session query, use dedicated rendering
                if root_info_c.get('session_source'):
                    session_info = root_info_c.get('session_info', {})
                    session_reason = root_info_c.get('session_reason', '')
                    print(f'   ℹ️  Data source: GetMySQLAllSessionAsync live session query')
                    print(f'   Session ID: {session_info.get("SessionId", "")}')
                    print(f'   User: {session_info.get("User", "")}')
                    print(f'   Client: {session_info.get("Client", "")}')
                    print(f'   Command: {session_info.get("Command", "")}')
                    print(f'   Exec time: {session_info.get("Time", 0)}s')
                    print(f'   Trx duration: {session_info.get("TrxDuration", 0)}s')
                    print(f'   SQL: {(session_info.get("SqlText", "") or "")[:200]}')
                    print(f'   Reason: {session_reason}')
                else:
                    root_dml_time_c = root_info_c.get('dml_time', '')
                
                    # Filter intermediate blocked threads
                    relevant_chain_members = []
                    for tid, info in blocked_in_chain:
                        dml_time = info.get('dml_time', '')
                        lock_time_val = info.get('lock_time', 0)
                        if lock_time > 10000:
                            # Row lock: intermediate blocked threads need high LockTime
                            if dml_time and root_dml_time_c < dml_time < lock_ref_utc_str and lock_time_val >= 100000:
                                relevant_chain_members.append((tid, info))
                        else:
                            # MDL lock: all threads with uncommitted transactions on same table are blockers
                            if (tid, info) != root_source:
                                relevant_chain_members.append((tid, info))
                    relevant_chain_members.sort(key=lambda x: x[1].get('dml_time', ''))
                    
                    # Get diagnosed thread transaction context
                    blocked_thread_info_c = thread_transactions.get(str(thread_id)) if thread_transactions else None
                    
                    # Render blocking chain (transaction timeline format, conclusion with 3-space indent)
                    self._render_blocking_chain(root_source, relevant_chain_members, thread_id, sql, problem_time, problem_time_utc_str, blocked_thread_info_c, blocked_sql_audit=target_blocked, indent='   ', lock_type='row' if lock_time > 10000 else 'mdl')
            else:
                print(f'   {lock_source_threads[0]} (lock holder) → {thread_id} (blocked)')
            print()
            print('💡 Recommendations:')
            print(f'   - Check thread {lock_source_threads[0]}  transaction for why it remains uncommitted')
            print('   - Optimize transaction granularity, reduce lock hold time')
            print('   - If application bug, fix uncommitted transaction issue')
        else:
            print('⚠️  Lock holder not clearly identified')
            print()
            print('💡 Recommendations:')
            print('   - Check for long-running transactions')
            print('   - Use DAS console to check current sessions')
            print('   - Check for DDL operations')
        
        print()



class SmartLockDiagnoser(LockDiagnosisAnalyzer):
    """CLI data fetcher - calls DAS API via aliyun CLI"""

    _ALLOWED_ACTIONS = frozenset({
        'GetDasSQLLogHotData', 'GetDeadLockHistory', 'GetDeadLockDetail',
        'CreateLatestDeadLockAnalysis', 'DescribeSqlLogConfig',
        'GetMySQLAllSessionAsync',
    })

    _plugins_ensured = False

    @classmethod
    def _ensure_cli_plugins(cls):
        if cls._plugins_ensured:
            return
        required = ['das']
        for product in required:
            plugin_name = f'aliyun-cli-{product}'
            try:
                check = subprocess.run(
                    ['aliyun', 'plugin', 'list'],
                    capture_output=True, text=True, timeout=30
                )
                if plugin_name in (check.stdout or ''):
                    continue
                install = subprocess.run(
                    ['aliyun', 'plugin', 'install', '--name', plugin_name],
                    capture_output=True, text=True, timeout=60
                )
                if install.returncode != 0:
                    print(f'  ⚠️  Plugin install {plugin_name} failed: {install.stderr.strip()}')
            except Exception as e:
                print(f'  ⚠️  Plugin ensure failed for {plugin_name}: {e}')
        cls._plugins_ensured = True

    def _call_das_api(self, action, **kwargs):
        import re
        import time as _time

        if action not in self._ALLOWED_ACTIONS:
            raise ValueError(f"Action not allowed: {action}")

        self._ensure_cli_plugins()

        cli_action = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', action)
        cli_action = re.sub(r'([a-z\d])([A-Z])', r'\1-\2', cli_action)
        cli_action = cli_action.lower()
        cli_action = cli_action.replace('my-sql', 'mysql')

        session_id = os.environ.get('SKILL_SESSION_ID', 'unknown')
        ua = f'AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session_id}'

        cmd = [
            'aliyun', 'das', cli_action,
            '--endpoint', 'das.cn-shanghai.aliyuncs.com',
            '--user-agent', ua
        ]

        for key, value in kwargs.items():
            cli_key = re.sub(r'([a-z\d])([A-Z])', r'\1-\2', key).lower()
            cmd.extend([f'--{cli_key}', str(value)])

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    if 'Throttling' in error_msg or 'throttling' in error_msg or 'Busy' in error_msg:
                        if attempt < max_attempts - 1:
                            wait = 3 ** (attempt + 1)
                            print(f'  ⚠️  Throttled [{action}], retry in {wait}s (attempt {attempt + 1}/{max_attempts})')
                            _time.sleep(wait)
                            continue
                    if 'Forbidden' in error_msg or 'AccessDenied' in error_msg:
                        raise PermissionError(f"Permission denied: {error_msg}")
                    elif 'InvalidParameter' in error_msg:
                        raise ValueError(f"Invalid parameter: {error_msg}")
                    elif 'InstanceNotFound' in error_msg or '-404' in error_msg:
                        raise FileNotFoundError(f"Instance not found: {error_msg}")
                    else:
                        raise Exception(f"CLI call failed [{action}]: {error_msg}")

                response_data = json.loads(result.stdout)
                return response_data

            except subprocess.TimeoutExpired:
                if attempt < max_attempts - 1:
                    wait = 3 ** (attempt + 1)
                    print(f'  ⚠️  Timeout [{action}], retry in {wait}s (attempt {attempt + 1}/{max_attempts})')
                    _time.sleep(wait)
                    continue
                raise TimeoutError(f"CLI call timeout [{action}], exceeded 60s after {max_attempts} attempts")
            except (PermissionError, ValueError, FileNotFoundError):
                raise
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse CLI response: {e}\nRaw output: {result.stdout[:200]}")
            except FileNotFoundError:
                raise Exception("aliyun CLI not found, please install: https://help.aliyun.com/zh/cli/")

    def query_sql_logs_by_where_condition(self, table_name, where_conditions, start_ms, end_ms, max_pages=5):
        """
        Query SQL logs by table name and WHERE conditions
        
        Server-side filtering using QueryKeyword + LogicalOperator=and:
        - When where_conditions is not None: QueryKeyword = 'column value table_name'
          e.g. UPDATE accounts WHERE id=1 -> QueryKeyword='id 1 accounts'
        - When where_conditions is None: QueryKeyword='table_name'
        """
        all_logs = []
        page_number = 1
        
        # DML keywords (client-side secondary filter)
        dml_keywords = ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']
        
        # Build QueryKeyword: column + value + table_name (space-separated)
        keyword_parts = [table_name]
        if where_conditions:
            for col, val in where_conditions.items():
                keyword_parts.append(col)
                keyword_parts.append(val)
        query_keyword = ' '.join(keyword_parts)
        
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'QueryKeyword': query_keyword,
                'LogicalOperator': 'and',
                'State': '0',
                'SortKey': 'OriginTime',
                'SortMethod': 'DESC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            
            logs = data.get('Data', {}).get('List', [])
            
            for log in logs:
                sql_lower = log.get('SQLText', '').lower()
                
                # Secondary filter: keep only DML or explicit locking statements
                if not any(kw in sql_lower for kw in dml_keywords):
                    continue
                
                all_logs.append(log)
            
            if len(logs) == 0:
                break
            
            page_number += 1
        
        return all_logs

    def query_long_running_selects(self, table_name, start_ms, end_ms, min_latency_us=60000000, max_pages=5):
        """
        Query long-running SELECT on the same table (Latancy >= min_latency_us)
        
        For MDL lock diagnosis: long-running SELECT holds shared MDL lock, blocking ALTER TABLE etc.
        min_latency_us: Minimum execution time threshold, default 60s = 60,000,000 microseconds
        
        Note: No State filter, because killed long SELECT still held MDL lock before being killed.
        DAS API time filter may use SQL end time, caller should pass a wide enough End time.
        """
        all_logs = []
        page_number = 1
        
        query_keyword = f'select {table_name}'
        
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'QueryKeyword': query_keyword,
                'LogicalOperator': 'and',
                'SortKey': 'OriginTime',
                'SortMethod': 'DESC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            
            logs = data.get('Data', {}).get('List', [])
            
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower()
                latency = log.get('Latancy', 0) or 0
                
                if sql_lower.strip().startswith('select') and latency >= min_latency_us:
                    all_logs.append(log)
            
            if len(logs) == 0:
                break
            
            page_number += 1
        
        return all_logs

    def query_table_selects(self, table_name, start_ms, end_ms, max_pages=5):
        """
        Query all SELECT statements on the same table (no Latancy filter)
        
        For MDL lock diagnosis: SELECT in transaction also holds shared MDL lock,
        if transaction is uncommitted, MDL lock is held until transaction ends.
        """
        all_logs = []
        page_number = 1
        
        query_keyword = f'select {table_name}'
        
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'QueryKeyword': query_keyword,
                'LogicalOperator': 'and',
                'State': '0',
                'SortKey': 'OriginTime',
                'SortMethod': 'DESC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            
            logs = data.get('Data', {}).get('List', [])
            
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower()
                # Keep SELECT statements (exclude SELECT FOR UPDATE and LOCK IN SHARE MODE, already covered in DML query)
                if sql_lower.strip().startswith('select') and 'for update' not in sql_lower and 'lock in share mode' not in sql_lower:
                    all_logs.append(log)
            
            if len(logs) == 0:
                break
            
            page_number += 1
        
        return all_logs

    def query_sql_logs_by_keywords(self, start_ms, end_ms, keywords, max_pages=10):
        """Query SQL logs by keywords

        Use DAS API QueryKeyword for server-side pre-filtering to avoid pagination truncation in large time windows.
        Multi-word keywords (e.g. 'lock tables') extract the most distinctive word for server-side filter, with client-side exact matching.
        """
        all_logs = []
        page_number = 1

        # Build server-side filter keywords: extract the most distinctive word from each keyword
        server_keywords = []
        if keywords:
            for kw in keywords:
                if ' ' not in kw:
                    server_keywords.append(kw)
                else:
                    # Multi-word keyword: take the longest word (usually most distinctive)
                    words = kw.split()
                    server_keywords.append(max(words, key=len))
        use_server_filter = bool(server_keywords)

        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '500',
            }

            # Server-side pre-filter: reduce result count, avoid data loss from pagination truncation
            if use_server_filter:
                params['QueryKeyword'] = ' '.join(server_keywords)
                params['LogicalOperator'] = 'or'
            
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            
            logs = data.get('Data', {}).get('List', [])
            total = data.get('Data', {}).get('Total', 0)
            
            # Client-side secondary filter for accuracy (server-side filter may have fuzzy matching)
            if keywords:
                filtered_logs = [
                    log for log in logs
                    if any(kw in log.get('SQLText', '').lower() for kw in keywords)
                ]
            else:
                filtered_logs = logs
            
            all_logs.extend(filtered_logs)
            
            if len(logs) == 0 or len(all_logs) >= total:
                break
            
            page_number += 1
        
        return all_logs

    def query_sql_logs_parallel(self, instance_id, problem_time):
        """Concurrently query multiple batches of SQL logs"""
        self.instance_id = instance_id
        
        # Define query batches (smart time range)
        query_batches = [
            {
                'name': 'Blocked SQL (State 1205/1317)',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': [],
                'post_filter': lambda log: str(log.get('State', '')) in ['1205', '1213', '1317']
            },
            {
                'name': 'DML operations (UPDATE/DELETE/INSERT)',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['update', 'delete', 'insert', 'replace']
            },
            {
                'name': 'SELECT FOR UPDATE (explicit locking)',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['for update', 'lock in share mode']
            },
            {
                'name': 'DDL operations (ALTER/CREATE/DROP)',
                'start': problem_time - timedelta(hours=1),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['alter', 'create', 'drop', 'truncate', 'rename']
            },
            {
                'name': 'Transaction control (BEGIN/COMMIT/ROLLBACK)',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['begin', 'start transaction', 'commit', 'rollback', 'set autocommit']
            },
            {
                'name': 'FLUSH operations',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['flush']
            },
            {
                'name': 'Lock operations (LOCK/UNLOCK)',
                'start': problem_time - timedelta(minutes=30),
                'end': problem_time + timedelta(minutes=10),
                'keywords': ['lock tables', 'unlock tables']
            },
        ]
        
        print(f"\n📊 Concurrent query {len(query_batches)} batches of SQL logs...")
        print()
        
        # Concurrent query
        all_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_batch = {}
            
            for batch in query_batches:
                start_ms = int(batch['start'].timestamp() * 1000)
                end_ms = int(batch['end'].timestamp() * 1000)
                
                future = executor.submit(
                    self.query_sql_logs_by_keywords,
                    start_ms, end_ms,
                    batch['keywords']
                )
                future_to_batch[future] = batch
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    logs = future.result()
                    
                    # Apply post-filter
                    if 'post_filter' in batch:
                        logs = [log for log in logs if batch['post_filter'](log)]
                    
                    all_results[batch['name']] = logs
                    print(f"  ✅ {batch['name']}: {len(logs)}  ")
                except Exception as e:
                    print(f"  ❌ {batch['name']}: Query failed - {e}")
                    all_results[batch['name']] = []
        
        # Merge all results
        merged_logs = []
        for logs in all_results.values():
            merged_logs.extend(logs)
        
        # Deduplicate (based on OriginTime + ThreadID + SQLText)
        unique_logs = {}
        for log in merged_logs:
            key = (log.get('OriginTime'), log.get('ThreadID'), log.get('SQLText'))
            unique_logs[key] = log
        
        return list(unique_logs.values()), all_results

    def query_transaction_controls(self, thread_ids, start_ms, end_ms, max_pages=3):
        """
        Query transaction control statements for specified threads (BEGIN/COMMIT/ROLLBACK/SET autocommit)
        Server-side filter using ThreadID parameter, DAS API limits 5 ThreadIDs per call
        """
        all_logs = []
        tc_keywords = ['begin', 'start transaction', 'commit', 'rollback', 'set autocommit', 'innodb_lock_wait_timeout', 'lock_wait_timeout', 'transaction_isolation', 'tx_isolation', 'transaction isolation', 'logout']

        # DAS API ThreadID supports max 5, batch query when exceeding
        BATCH_SIZE = 5
        thread_id_list = list(thread_ids)
        batches = [thread_id_list[i:i+BATCH_SIZE] for i in range(0, len(thread_id_list), BATCH_SIZE)]

        for batch in batches:
            thread_id_param = ' '.join(batch)
            page_number = 1
            while page_number <= max_pages:
                params = {
                    'InstanceId': self.instance_id,
                    'Start': str(start_ms),
                    'End': str(end_ms),
                    'ThreadID': thread_id_param,
                    'SortKey': 'OriginTime',
                    'SortMethod': 'ASC',
                    'PageNumbers': str(page_number),
                    'MaxRecordsPerPage': '100',
                }

                data = self._call_das_api('GetDasSQLLogHotData', **params)

                logs = data.get('Data', {}).get('List', [])

                for log in logs:
                    sql_text = log.get('SQLText', '').lower()
                    if any(kw in sql_text for kw in tc_keywords):
                        all_logs.append(log)

                if len(logs) == 0:
                    break
                page_number += 1

        return all_logs

    def query_tc_without_thread_filter(self, start_ms, end_ms, max_pages=3):
        """Query COMMIT/ROLLBACK/LOGOUT (all threads) for COMMIT-match."""
        all_logs = []
        tc_match = {'commit', 'rollback'}
        page_number = 1
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'QueryKeyword': 'commit rollback logout',
                'SortKey': 'OriginTime',
                'SortMethod': 'ASC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            logs = data.get('Data', {}).get('List', [])
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower().strip()
                first_word = sql_lower.split()[0] if sql_lower else ''
                if first_word in tc_match or 'logout' in sql_lower:
                    all_logs.append(log)
            if not logs:
                break
            page_number += 1
        return all_logs

    def query_thread_dml_on_table(self, thread_id, table_name, start_ms, end_ms, max_pages=3):
        """DAS: Query DML operations for specified threads on specified table."""
        all_logs = []
        dml_keywords = ['update', 'delete', 'insert', 'replace', 'for update', 'lock in share mode']
        table_lower = table_name.lower() if table_name else ''
        page_number = 1
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'ThreadID': str(thread_id),
                'QueryKeyword': table_name,
                'SortKey': 'OriginTime',
                'SortMethod': 'ASC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            logs = data.get('Data', {}).get('List', [])
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower()
                if table_lower and table_lower not in sql_lower:
                    continue
                if any(kw in sql_lower for kw in dml_keywords):
                    all_logs.append(log)
            if not logs:
                break
            page_number += 1
        return all_logs

    def query_thread_select_on_table(self, thread_id, table_name, start_ms, end_ms, max_pages=3):
        """DAS: Query plain SELECT for specified threads on specified table (SERIALIZABLE detection)."""
        all_logs = []
        table_lower = table_name.lower() if table_name else ''
        page_number = 1
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'ThreadID': str(thread_id),
                'QueryKeyword': table_name,
                'SortKey': 'OriginTime',
                'SortMethod': 'ASC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            logs = data.get('Data', {}).get('List', [])
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower()
                if not sql_lower.strip().startswith('select'):
                    continue
                if table_lower and table_lower not in sql_lower:
                    continue
                if 'for update' in sql_lower or 'lock in share mode' in sql_lower:
                    continue
                all_logs.append(log)
            if not logs:
                break
            page_number += 1
        return all_logs

    def query_serializable_threads(self, start_ms, end_ms, max_pages=2):
        """DAS: Query all SET ... SERIALIZABLE statements in time window, return involved thread IDs."""
        thread_ids = set()
        page_number = 1
        while page_number <= max_pages:
            params = {
                'InstanceId': self.instance_id,
                'Start': str(start_ms),
                'End': str(end_ms),
                'QueryKeyword': 'SERIALIZABLE',
                'SortKey': 'OriginTime',
                'SortMethod': 'ASC',
                'PageNumbers': str(page_number),
                'MaxRecordsPerPage': '100',
            }
            data = self._call_das_api('GetDasSQLLogHotData', **params)
            logs = data.get('Data', {}).get('List', [])
            for log in logs:
                sql_lower = (log.get('SQLText', '') or '').lower()
                if 'serializable' in sql_lower and 'set' in sql_lower:
                    tid = str(log.get('ThreadID', ''))
                    if tid and tid != '0':
                        thread_ids.add(tid)
            if not logs:
                break
            page_number += 1
        return thread_ids

    def query_all_sessions(self):
        """Query all current sessions using GetMySQLAllSessionAsync

        This is a read-only operation, no database credentials required.
        Fallback when audit log cannot find lock holder, check active sessions.

        Returns: SessionData dict or None
        """
        import time as _time

        # First call: get ResultId
        result = self._call_das_api('GetMySQLAllSessionAsync', InstanceId=self.instance_id)
        
        result_id = result.get('Data', {}).get('ResultId')
        is_finish = result.get('Data', {}).get('IsFinish', False)
        
        if not result_id:
            print('  ⚠️  GetMySQLAllSessionAsync did not return ResultId')
            return None
        
        # Poll until complete
        max_retries = 10
        retry = 0
        while not is_finish and retry < max_retries:
            _time.sleep(2)
            result = self._call_das_api('GetMySQLAllSessionAsync', InstanceId=self.instance_id, ResultId=result_id)
            is_finish = result.get('Data', {}).get('IsFinish', False)
            retry += 1
        
        if not is_finish:
            print('  ⚠️  GetMySQLAllSessionAsync timed out')
            return None

        return result.get('Data', {}).get('SessionData', {})


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Smart lock wait diagnosis for PolarDB/RDS MySQL')
    parser.add_argument('--instance-id', required=True, help='Instance ID (rm-xxx or pc-xxx)')
    parser.add_argument('--time', required=True, help='Problem time in Beijing time (e.g. "2026-06-08 17:02:35.894")')
    parser.add_argument('--thread-id', required=True, type=int, help='Blocked thread ID')
    parser.add_argument('--sql', required=True, help='Blocked SQL statement')
    parser.add_argument('--region', default='cn-hangzhou', help='Region (default: cn-hangzhou)')

    # Support both argparse and legacy positional args
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-'):
        instance_id = sys.argv[1]
        problem_time_str = sys.argv[2]
        thread_id = int(sys.argv[3])
        sql = sys.argv[4]
        region = sys.argv[5] if len(sys.argv) > 5 else 'cn-hangzhou'
    else:
        args = parser.parse_args()
        instance_id = args.instance_id
        problem_time_str = args.time
        thread_id = args.thread_id
        sql = args.sql
        region = args.region

    diagnoser = SmartLockDiagnoser(instance_id=instance_id, region=region)
    diagnoser.diagnose(
        instance_id=instance_id,
        problem_time_str=problem_time_str,
        thread_id=thread_id,
        sql=sql
    )


if __name__ == '__main__':
    main()
