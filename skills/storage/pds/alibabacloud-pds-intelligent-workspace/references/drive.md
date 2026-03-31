# PDS Drive Concepts and API Reference

**Scenario**: Used when querying user's drive list (including personal space, enterprise space, team space, all spaces)
**Purpose**: Get drive_id for user's personal space, team space, and enterprise space

---

### Drive Concept Introduction
A PDS drive is a cloud storage space that can store files. A drive must have an owner, which can be either a user or a group.
- When a drive belongs to a user, it is that user's personal space.
- When a drive belongs to an enterprise group, it is an enterprise space.
- When a drive belongs to a team group, it is a team space.

#### Users have three types of spaces in a domain:
- Enterprise space
- Team space
- Personal space

**When referring to "my PDS drive" without specifying which type of space, it should be understood as all spaces: including enterprise space, team space, and personal space**

### Drive Query API Reference

#### Query Method for Enterprise Space and Team Space
You can query using the list group drives API. The items field in the response contains the user's team space list, and the root_group_drive field contains the enterprise space object.
```bash
aliyun pds list-my-group-drive --limit 100 --marker "" --user-agent AlibabaCloud-Agent-Skills
```

**Output**: Returns JSON containing enterprise space and team space, including `items`, `root_group_drive`, `next_marker`, etc. Detailed explanation:
- items: Contains team space list. There may be multiple team spaces. If not all displayed on one page, next_marker will be returned. If there are no team spaces, this field returns empty.
- root_group_drive: Contains enterprise space object. There is at most one enterprise space. If none exists, this field returns empty.
- next_marker: Used for pagination, indicates the marker for next page. Pass the returned next_marker to the marker parameter to query the next page. If no next page, this field returns empty.

The JSON objects returned in items and root_group_drive are Drive objects. Important attributes of Drive objects include:
- drive_id: Unique space ID, commonly used in API parameters to identify a drive (important parameter for identifying a space, other APIs may require this field as input)
- drive_name: Space name, commonly used for display
- total_size: Total space size in bytes
- used_size: Used space size in bytes
- owner_type: Owner type, either user or group
- owner: Owner ID

**Example Output**:
```json
{
  "items": [
    {
      "category": "",
      "created_at": "2026-03-22T06:00:12.951Z",
      "creator": "a34527b***c381b23f3",
      "description": "",
      "domain_id": "bj12",
      "drive_id": "100",
      "drive_name": "Test Team Space 1",
      "drive_type": "normal",
      "encrypt_data_access": false,
      "encrypt_mode": "none",
      "owner": "e71ce9***c5862d5",
      "owner_type": "group",
      "permission": null,
      "relative_path": "",
      "status": "enabled",
      "store_id": "fb651***943990a",
      "total_size": 107374182400,
      "updated_at": "2026-03-22T06:00:12.952Z",
      "used_size": 138194
    },
    {
      "category": "",
      "created_at": "2026-03-22T06:00:12.951Z",
      "creator": "a34527***81b23f3",
      "description": "",
      "domain_id": "bj12",
      "drive_id": "101",
      "drive_name": "Test Team Space 2",
      "drive_type": "normal",
      "encrypt_data_access": false,
      "encrypt_mode": "none",
      "owner": "e71ce9***b7fc5862d5",
      "owner_type": "group",
      "permission": null,
      "relative_path": "",
      "status": "enabled",
      "store_id": "fb6516****45c943990a",
      "total_size": 107374182400,
      "updated_at": "2026-03-22T06:00:12.952Z",
      "used_size": 138194
    }
  ],
  "next_marker": "",
  "root_group_drive": {
    "category": "",
    "created_at": "2026-03-22T05:55:03.280Z",
    "creator": "system",
    "description": "",
    "domain_id": "bj12",
    "drive_id": "103",
    "drive_name": "Test Space",
    "drive_type": "normal",
    "encrypt_data_access": false,
    "encrypt_mode": "none",
    "owner": "9c251e****b9f952f",
    "owner_type": "group",
    "permission": null,
    "relative_path": "",
    "status": "enabled",
    "store_id": "fb651****43990a",
    "total_size": 107374182400,
    "updated_at": "2026-03-23T07:08:40.098Z",
    "used_size": 240062520
  }
}
```

In the above example output, team space drive_ids are: 100 and 101, enterprise space drive_id is: 103

#### Query API for Personal Space
You can query using the list my drives API. The items field in the response contains the user's personal space list.
```bash
aliyun pds list-my-drives --limit 100 --marker "" --user-agent AlibabaCloud-Agent-Skills
```

The JSON array in the items field returned by the personal space query API contains personal space Drive objects. Important attributes of Drive objects include:
- drive_id: Unique space ID, commonly used in API parameters to identify a drive (important parameter for identifying a space, other APIs may require this field as input)
- drive_name: Space name, commonly used for display
- total_size: Total space size in bytes
- used_size: Used space size in bytes
- owner_type: Owner type, either user or group
- owner: Owner ID

```json
{
    "items": [
        {
            "category": "",
            "created_at": "2026-03-22T05:59:33.037Z",
            "creator": "a34527b***81b23f3",
            "description": "",
            "domain_id": "bj31216",
            "drive_id": "108",
            "drive_name": "SuperAdmin (Test)",
            "drive_type": "normal",
            "encrypt_data_access": false,
            "encrypt_mode": "none",
            "owner": "a34527b***81b23f3",
            "owner_type": "user",
            "permission": null,
            "relative_path": "",
            "status": "enabled",
            "store_id": "fb6516***c943990a",
            "total_size": 107374182400,
            "updated_at": "2026-03-23T08:45:35.541Z",
            "used_size": 950709133
        }
    ],
    "next_marker": ""
}
```

In the above example output, personal space drive_id is 108