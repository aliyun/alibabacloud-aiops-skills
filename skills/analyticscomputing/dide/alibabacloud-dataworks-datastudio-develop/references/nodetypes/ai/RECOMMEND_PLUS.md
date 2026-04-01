# Recommendation Engine (RECOMMEND_PLUS)

## Overview

- Compute engine: `ALGORITHM`
- Content format: json
- Extension: `.json`
- Data source type: `pai`
- Description: Scheduling node for Alibaba Cloud Intelligent Recommendation (AIRec) in DataWorks, for periodically updating recommendation data

The RECOMMEND_PLUS node incorporates Alibaba Cloud Intelligent Recommendation Engine data processing tasks into the DataWorks scheduling system. Through this node, users can perform unified periodic scheduling management of tasks such as recommendation engine data backflow, feature processing, and model training, ensuring that recommendation data updates are coordinated with upstream and downstream data processing workflows.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_recommend_plus",
        "script": {
          "path": "example_recommend_plus",
          "runtime": { "command": "RECOMMEND_PLUS" },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Restrictions

- Alibaba Cloud Intelligent Recommendation (AIRec) service must be activated first, and the corresponding PAI data source must be bound in the DataWorks workspace
- Node content is in JSON format; the specific configuration structure is defined by the Intelligent Recommendation Engine
