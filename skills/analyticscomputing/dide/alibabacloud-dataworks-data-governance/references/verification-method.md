# Success Verification — DataWorks Data Governance Tag Management

## Common Response Structure

All APIs return a unified response structure:

```json
{
  "RequestId": "0bc14115****159376359",
  "Message": "success",
  "Code": "0",
  "Data": true
}
```

**Success criteria:**
- HTTP status code == `200`
- `Data` == `true` (create/update/bind/unbind operations)
- `Data` is an object (ListDataAssetTags, ListDataAssets)

---

## Verification Steps by Operation

### 1. Verify CreateDataAssetTag

```python
response = create_data_asset_tag(client, key='test_key', values=['v1'], description='test')
body = response.get('body', {})
assert response.get('statusCode') == 200
assert body.get('Data') == True, f"Create failed: {body.get('Message')}"
print(f"[OK] Tag key 'test_key' created. RequestId={body.get('RequestId')}")

# Confirm the tag key appears in the list
list_resp = list_data_asset_tags(client, key='test_key')
tags = list_resp.get('body', {}).get('Data', {}).get('DataAssetTags', [])
assert any(t.get('Key') == 'test_key' for t in tags), "Tag key not found in list"
print("[OK] ListDataAssetTags verification passed")
```

### 2. Verify UpdateDataAssetTag

```python
response = update_data_asset_tag(client, key='test_key', values=['v1', 'v2'], description='updated')
body = response.get('body', {})
assert body.get('Data') == True, f"Update failed: {body.get('Message')}"
print("[OK] Tag key updated successfully")
```

### 3. Verify ListDataAssetTags

```python
response = list_data_asset_tags(client, page_number=1, page_size=10)
body = response.get('body', {})
data = body.get('Data', {})
assert 'TotalCount' in data, "Response missing TotalCount"
assert 'DataAssetTags' in data, "Response missing DataAssetTags"
print(f"[OK] Found {data.get('TotalCount')} tag keys, {len(data.get('DataAssetTags', []))} on this page")
```

### 4. Verify ListDataAssets

```python
response = list_data_assets(client, asset_type='Table', page_number=1, page_size=10)
body = response.get('body', {})
data = body.get('Data', {})
assert response.get('statusCode') == 200, f"HTTP error: {response.get('statusCode')}"
assert 'TotalCount' in data, "Response missing TotalCount"
assert 'DataAssets' in data, "Response missing DataAssets"
print(f"[OK] Found {data.get('TotalCount')} assets, {len(data.get('DataAssets', []))} on this page")
```

### 6. Verify TagDataAssets

```python
response = tag_data_assets(
    client,
    tags=[{"Key": "test_key", "Value": "v1"}],
    data_asset_ids=["maxcompute-table.my_project.my_table"],
    data_asset_type="ACS::DataWorks::Table"
)
body = response.get('body', {})
assert body.get('Data') == True, f"Bind failed: {body.get('Message')}"
print("[OK] Tag bound to asset successfully")
```

### 7. Verify UnTagDataAssets

```python
response = untag_data_assets(
    client,
    tags=[{"Key": "test_key", "Value": "v1"}],
    data_asset_ids=["maxcompute-table.my_project.my_table"],
    data_asset_type="ACS::DataWorks::Table"
)
body = response.get('body', {})
assert body.get('Data') == True, f"Unbind failed: {body.get('Message')}"
print("[OK] Tag unbound from asset successfully")
```

---

## Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `0` | Success | — |
| `210400101` | Invalid parameter | Check required fields and value formats |
| `Forbidden` | Insufficient permissions | Review RAM policies in `ram-policies.md` |
| `Throttling` | Request rate exceeded | Retry with exponential backoff |
| `InternalError` | Server-side error | Record RequestId and contact support |
