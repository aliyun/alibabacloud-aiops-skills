"""Base class for address book type plugins"""
from abc import ABC, abstractmethod


class AddressBookPlugin(ABC):
    """Base class for address book type plugins; all plugins must inherit it and implement the following attributes"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name (Chinese, used for display and interactive selection)"""
        pass

    @property
    @abstractmethod
    def group_types(self) -> list:
        """API GroupTypes combination (flat format parameters)
        Example: ['ip', 'ipv6']  -> GroupTypes.1=ip & GroupTypes.2=ipv6
        """
        pass

    @property
    @abstractmethod
    def sheet_name(self) -> str:
        """Excel sheet name"""
        pass

    @property
    @abstractmethod
    def columns(self) -> list:
        """Excel column definitions: [(column_name, getter_function), ...]
        Getter function signature: (item: dict) -> any
        """
        pass

    @property
    def api_action(self) -> str:
        """API Action name, defaults to DescribeAddressBook"""
        return "DescribeAddressBook"

    @property
    def page_no_key(self) -> str:
        """Page number parameter name, defaults to CurrentPage"""
        return "CurrentPage"

    @property
    def result_key(self) -> str:
        """Key name of the returned data array, defaults to Acls"""
        return "Acls"

    @property
    def order(self) -> int:
        """Sort order (smaller comes first, defaults to 0)"""
        return 0

    @property
    def col_widths(self) -> list:
        """Column widths (optional), one-to-one correspondence with columns"""
        return None

    def post_process(self, items: list) -> list:
        """Data post-processing (optional override)
        Default: filter out system built-in address books with Global=1
        """
        return [item for item in items if item.get("Global", 0) != 1]

    def extra_params(self) -> dict:
        """Extra API request parameters (optional override)"""
        return {}
    
    def custom_fetch(self, ak, sk, endpoint, call_api_fn, page_size=50, security_token=None):
        """Custom data fetching logic (optional override)
        If None is returned, the default fetch logic is used
        If a data list is returned, the returned data is used directly
        """
        return None

    # ==================== Restore-related attributes ====================

    @property
    def restore_api(self) -> str:
        """API Action called during restore"""
        return "AddAddressBook"

    @property
    def restore_column_mapping(self) -> dict:
        """Mapping from Excel column names to API parameters
        Format: {"Excel column name": "API parameter name"}
        """
        return {}

    @property
    def restore_value_transforms(self) -> dict:
        """Transform functions for API parameter values
        Format: {"API parameter name": transform_fn}
        transform_fn signature: (value) -> new_value
        """
        return {}

    @property
    def restore_static_params(self) -> dict:
        """Fixed API parameters during restore (not read from Excel)"""
        return {}

    @property
    def restore_skip_params_by_type(self) -> dict:
        """Dynamically skip other parameters based on the value of a given field
        Format: {"field name to check": {"field value": [list of parameters to skip]}}
        Example: {"PrivateDnsType": {"PrivateZone": ["PrimaryDns", "StandbyDns"]}}
        """
        return {}

    @property
    def name_column(self) -> str:
        """Excel column name that identifies the record name (used for log output)"""
        return "地址簿名称"

    @property
    def uid_column(self) -> str:
        """UUID field name in the API response (used to determine whether creation succeeded)"""
        return "GroupUuid"

    def post_restore_record(self, row, result, ak, sk, endpoint, call_api_fn, security_token=None):
        """Hook after a single record is restored successfully (can be overridden by subclasses)
        Does nothing by default.
        """
        pass

    def restore(self, ak, sk, region, call_api_fn, excel_file, security_token=None):
        """
        Generic restore logic: read data from Excel, call the API to create resources in reverse order, and update the restore status.
        
        If a plugin needs fully custom restore logic, it can override this method.
        
        Returns: (success_count, fail_count, skip_count, exist_count)
        """
        import pandas as pd

        # Build endpoint
        endpoint = f"cloudfw.{region}.aliyuncs.com"

        # Skip if the sheet does not exist (categories with no data at backup time have no sheet)
        if self.sheet_name not in pd.ExcelFile(excel_file).sheet_names:
            print(f"  [{self.name}] no sheet '{self.sheet_name}' in the backup file, skipping (no data at backup time)")
            return (0, 0, 0, 0)

        # Read Excel
        df = pd.read_excel(excel_file, sheet_name=self.sheet_name)
        print(f"  [{self.name}] loaded {len(df)} records")

        # Add the restore status column
        if '恢复状态' not in df.columns:
            df['恢复状态'] = '待恢复'
        else:
            # Ensure the restore status column is of string type (avoid float64 being unable to hold strings)
            df['恢复状态'] = df['恢复状态'].astype(str).replace('nan', '待恢复')

        column_mapping = self.restore_column_mapping
        value_transforms = self.restore_value_transforms
        static_params = self.restore_static_params
        name_col = self.name_column

        if not column_mapping:
            print(f"  [{self.name}] [FAIL] restore_column_mapping not configured, cannot restore")
            return (0, len(df), 0, 0)

        success_count = 0
        fail_count = 0
        skip_count = 0
        exist_count = 0

        # Iterate in reverse order (from the last row, so the display order matches the table)
        # Use a list to store indices, avoiding index issues caused by modifying df while iterating
        indices = list(range(len(df) - 1, -1, -1))
        
        for idx in indices:
            row = df.iloc[idx]
            record_name = str(row.get(name_col, f"record{idx+1}"))

            # Skip if already restored successfully
            current_status = df.at[df.index[idx], '恢复状态']
            if current_status == '成功':
                skip_count += 1
                continue

            # Build API parameters
            api_params = {}
            for excel_col, api_param in column_mapping.items():
                value = row.get(excel_col, '')
                
                # Handle empty values
                if pd.isna(value) or str(value).strip() == '' or str(value).strip() == '(空)':
                    continue
                
                value = str(value)
                
                # Apply value transforms (looked up by the original snake_case name)
                if api_param in value_transforms:
                    value = value_transforms[api_param](value)
                
                # Skip if the transform result is None
                if value is None:
                    continue
                
                # Use the API parameter name defined by the plugin directly (no auto conversion)
                api_params[api_param] = value

            # Add static parameters
            api_params.update(static_params)

            # Dynamically skip parameters by type
            skip_params_by_type = self.restore_skip_params_by_type
            for check_param, skip_map in skip_params_by_type.items():
                current_value = api_params.get(check_param)
                if current_value and str(current_value) in skip_map:
                    for param_to_skip in skip_map[str(current_value)]:
                        api_params.pop(param_to_skip, None)

            # Handle list-type parameters (flattening)
            # Note: keys are already in PascalCase format here (e.g. FirewallType)
            flattened_params = {}
            for key, value in api_params.items():
                if isinstance(value, list):
                    # Flatten list parameters: FirewallType -> FirewallType.1, FirewallType.2
                    for i, item in enumerate(value, 1):
                        flattened_params[f"{key}.{i}"] = item
                else:
                    flattened_params[key] = value
            
            api_params = flattened_params

            print(f"  [{self.name}] [{idx+1}] restoring: {record_name}")
            print(f"    API params: {api_params}")

            try:
                result = call_api_fn(ak, sk, endpoint, self.restore_api, api_params, security_token)
                print(f"    API response: {result}")

                # Determine whether it succeeded
                if self.uid_column in result and result[self.uid_column]:
                    print(f"    [OK] success, {self.uid_column}: {result[self.uid_column]}")
                    df.at[df.index[idx], '恢复状态'] = '成功'
                    success_count += 1
                    # Hook after successful restore (can be overridden by subclasses)
                    self.post_restore_record(row, result, ak, sk, endpoint, call_api_fn, security_token)
                else:
                    # Check whether there is an error code
                    code = result.get("Code", "")
                    message = result.get("Message", "")
                    if "ErrorAddressGroupExist" in code or "already exists" in message.lower() or "Duplicates" in code:
                        print(f"    [WARN] already exists")
                        df.at[df.index[idx], '恢复状态'] = '已存在'
                        exist_count += 1
                    else:
                        print(f"    [FAIL] failed: {code} - {message}")
                        df.at[df.index[idx], '恢复状态'] = '失败'
                        fail_count += 1

            except Exception as e:
                error_str = str(e)
                if "ErrorAddressGroupExist" in error_str or "already exist" in error_str.lower() or "Duplicates" in error_str:
                    print(f"    [WARN] already exists")
                    df.at[df.index[idx], '恢复状态'] = '已存在'
                    exist_count += 1
                else:
                    print(f"    [FAIL] exception: {error_str[:200]}")
                    df.at[df.index[idx], '恢复状态'] = '失败'
                    fail_count += 1

        # Update the restore status in Excel
        import openpyxl
        wb = openpyxl.load_workbook(excel_file)
        ws = wb[self.sheet_name]

        # Find the restore status column (add it if it does not exist)
        header_row = [cell.value for cell in ws[1]]
        if '恢复状态' in header_row:
            status_col_idx = header_row.index('恢复状态') + 1
        else:
            status_col_idx = ws.max_column + 1
            ws.cell(row=1, column=status_col_idx, value='恢复状态')

        for i, (_, row) in enumerate(df.iterrows()):
            ws.cell(row=i + 2, column=status_col_idx, value=row.get('恢复状态', '待恢复'))

        wb.save(excel_file)

        print(f"  [{self.name}] restore finished: success {success_count}, fail {fail_count}, skip {skip_count}, existing {exist_count}")
        return (success_count, fail_count, skip_count, exist_count)
