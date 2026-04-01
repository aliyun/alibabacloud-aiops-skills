# Example 03: SQL Inter-Node Dependency

Two ODPS SQL nodes where dwd_order_detail depends on ods_order.

## File Structure

```
ods_order/
├── ods_order.spec.json
├── ods_order.sql
└── dataworks.properties
dwd_order_detail/
├── dwd_order_detail.spec.json
├── dwd_order_detail.sql
└── dataworks.properties
```
