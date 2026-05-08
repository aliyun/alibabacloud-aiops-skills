# PAI-Rec Engine Configuration Examples

This document provides sample PAI-Rec engine configurations and common patterns to help with validation and diagnosis.

## Configuration Structure Overview

A typical PAI-Rec engine configuration contains these main sections:

```json
{
  "scene_id": "default",
  "recall": {
    "modules": []
  },
  "rank": {
    "modules": []
  },
  "filter": {
    "rules": []
  },
  "experiment": {
    "layers": []
  }
}
```

---

## Basic Configuration Example

### Minimal Working Configuration

```json
{
  "scene_id": "embedding_recall_scene",
  "recall": {
    "modules": [
      {
        "name": "embedding_recall",
        "type": "vector",
        "params": {
          "table": "user_item_embedding",
          "index_type": "hnsw",
          "topk": 100,
          "timeout_ms": 200
        }
      }
    ]
  },
  "rank": {
    "modules": [
      {
        "name": "simple_scorer",
        "type": "feature_based",
        "params": {
          "features": ["user_age", "item_category", "click_rate"],
          "model_endpoint": "http://eas-service.cn-hangzhou.aliyuncs.com/scoring"
        }
      }
    ]
  },
  "filter": {
    "rules": [
      {
        "name": "basic_filter",
        "type": "threshold",
        "params": {
          "min_score": 0.1,
          "max_results": 50
        }
      }
    ]
  }
}
```

---

## Recall Module Examples

### 1. Vector Similarity Recall

```json
{
  "recall": {
    "modules": [
      {
        "name": "user_embedding_recall",
        "type": "vector",
        "params": {
          "table": "user_item_embeddings_v2",
          "index_type": "hnsw",
          "metric": "cosine",
          "topk": 500,
          "timeout_ms": 300,
          "filters": {
            "category": "electronics",
            "status": "active"
          }
        }
      }
    ]
  }
}
```

**Common Parameters:**
- `table`: Source embedding table name
- `index_type`: `hnsw`, `flat`, `ivf`
- `metric`: `cosine`, `euclidean`, `inner_product`
- `topk`: Number of results to retrieve
- `timeout_ms`: Query timeout
- `filters`: Pre-filter conditions

**Validation Checks:**
- ✅ Table exists and is accessible
- ✅ Index type is supported
- ✅ Metric matches index configuration
- ✅ Timeout is reasonable (50-500ms)
- ⚠️  topk too large (>1000) may impact performance

---

### 2. Collaborative Filtering Recall

```json
{
  "recall": {
    "modules": [
      {
        "name": "cf_recall",
        "type": "collaborative_filtering",
        "params": {
          "table": "user_behavior_matrix",
          "algorithm": "item_cf",
          "topk": 200,
          "min_similarity": 0.3,
          "decay_days": 30
        }
      }
    ]
  }
}
```

**Common Parameters:**
- `algorithm`: `user_cf`, `item_cf`, `swing`
- `min_similarity`: Minimum similarity threshold
- `decay_days`: Time decay for historical data

---

### 3. Hot Items Recall

```json
{
  "recall": {
    "modules": [
      {
        "name": "hot_items",
        "type": "popular",
        "params": {
          "table": "item_popularity_stats",
          "time_window_hours": 24,
          "category_aware": true,
          "topk": 100
        }
      }
    ]
  }
}
```

---

### 4. Multiple Recall Modules

```json
{
  "recall": {
    "modules": [
      {
        "name": "embedding_recall",
        "type": "vector",
        "weight": 0.5,
        "params": {
          "table": "embeddings",
          "topk": 300
        }
      },
      {
        "name": "cf_recall",
        "type": "collaborative_filtering",
        "weight": 0.3,
        "params": {
          "table": "user_behavior",
          "topk": 200
        }
      },
      {
        "name": "hot_items",
        "type": "popular",
        "weight": 0.2,
        "params": {
          "topk": 100
        }
      }
    ],
    "merge_strategy": "weighted",
    "final_topk": 500
  }
}
```

**Validation Checks:**
- ✅ Weights sum to 1.0 (if using weighted strategy)
- ✅ No duplicate module names
- ✅ final_topk >= max individual topk
- ⚠️  Too many modules may slow processing

---

## Rank Module Examples

### 1. Feature-Based Ranking

```json
{
  "rank": {
    "modules": [
      {
        "name": "feature_ranker",
        "type": "feature_based",
        "params": {
          "features": [
            "user_age",
            "user_gender",
            "item_category",
            "item_price",
            "ctr_7d",
            "cvr_7d"
          ],
          "feature_tables": {
            "user_features": "user_profile_v1",
            "item_features": "item_attributes_v1",
            "behavior_features": "user_item_stats_v1"
          },
          "model_endpoint": "http://eas.cn-hangzhou.aliyuncs.com/rank_model_v2",
          "timeout_ms": 100,
          "batch_size": 50
        }
      }
    ]
  }
}
```

**Validation Checks:**
- ✅ All feature tables accessible
- ✅ Model endpoint reachable
- ✅ Batch size reasonable (20-100)
- ✅ Timeout appropriate for batch size
- ⚠️  Too many features (>50) may slow inference

---

### 2. Multi-Stage Ranking

```json
{
  "rank": {
    "modules": [
      {
        "name": "coarse_ranker",
        "type": "simple_scorer",
        "stage": 1,
        "params": {
          "features": ["ctr_7d", "cvr_7d"],
          "topk": 200
        }
      },
      {
        "name": "fine_ranker",
        "type": "deep_model",
        "stage": 2,
        "params": {
          "model_endpoint": "http://eas.cn-hangzhou.aliyuncs.com/dnn_ranker",
          "features": ["all"],
          "topk": 50
        }
      }
    ]
  }
}
```

---

## Filter Module Examples

### 1. Threshold Filters

```json
{
  "filter": {
    "rules": [
      {
        "name": "score_threshold",
        "type": "threshold",
        "params": {
          "field": "score",
          "min_value": 0.1,
          "max_value": 1.0
        }
      },
      {
        "name": "diversity_filter",
        "type": "diversity",
        "params": {
          "field": "category",
          "max_same_category": 5
        }
      }
    ]
  }
}
```

---

### 2. Bloom Filter (Dedupe)

```json
{
  "filter": {
    "rules": [
      {
        "name": "dedupe_filter",
        "type": "bloom",
        "params": {
          "table": "user_exposure_history",
          "window_days": 7,
          "field": "item_id"
        }
      }
    ]
  }
}
```

---

### 3. Business Rules Filter

```json
{
  "filter": {
    "rules": [
      {
        "name": "business_rules",
        "type": "custom",
        "params": {
          "rules": [
            {
              "condition": "item_status == 'active'",
              "action": "keep"
            },
            {
              "condition": "item_price > user_budget",
              "action": "remove"
            },
            {
              "condition": "item_stock < 1",
              "action": "remove"
            }
          ]
        }
      }
    ]
  }
}
```

**Validation Checks:**
- ✅ Condition syntax is valid
- ✅ Referenced fields exist
- ✅ Actions are valid (keep/remove)
- ⚠️  Complex rules may impact performance

---

## Experiment Configuration Examples

### 1. A/B Testing

```json
{
  "experiment": {
    "enabled": true,
    "layers": [
      {
        "layer_id": "rank_model_ab_test",
        "experiments": [
          {
            "exp_id": "exp_baseline",
            "traffic": 0.5,
            "config": {
              "rank": {
                "modules": [
                  {
                    "name": "baseline_ranker",
                    "model_endpoint": "http://eas/baseline_model"
                  }
                ]
              }
            }
          },
          {
            "exp_id": "exp_new_model",
            "traffic": 0.5,
            "config": {
              "rank": {
                "modules": [
                  {
                    "name": "new_ranker",
                    "model_endpoint": "http://eas/new_model_v2"
                  }
                ]
              }
            }
          }
        ]
      }
    ]
  }
}
```

**Validation Checks:**
- ✅ Traffic percentages sum to 1.0
- ✅ Experiment IDs are unique
- ✅ Config overrides are valid
- ⚠️  Too many experiments may complicate analysis

---

## Common Configuration Patterns

### Pattern 1: E-commerce Recommendation

```json
{
  "scene_id": "product_recommendation",
  "recall": {
    "modules": [
      {
        "name": "user_embedding",
        "type": "vector",
        "params": {
          "table": "user_item_embeddings",
          "topk": 300
        }
      },
      {
        "name": "browse_history_cf",
        "type": "collaborative_filtering",
        "params": {
          "table": "browse_behavior",
          "topk": 200
        }
      },
      {
        "name": "trending_products",
        "type": "popular",
        "params": {
          "time_window_hours": 24,
          "topk": 100
        }
      }
    ],
    "merge_strategy": "weighted"
  },
  "rank": {
    "modules": [
      {
        "name": "ctr_cvr_ranker",
        "type": "feature_based",
        "params": {
          "features": ["user_profile", "item_attributes", "ctr_cvr_features"],
          "model_endpoint": "http://eas/rank_model"
        }
      }
    ]
  },
  "filter": {
    "rules": [
      {
        "name": "in_stock_filter",
        "type": "custom",
        "params": {
          "condition": "item_stock > 0"
        }
      },
      {
        "name": "exposure_dedupe",
        "type": "bloom",
        "params": {
          "table": "user_exposure",
          "window_days": 3
        }
      },
      {
        "name": "diversity",
        "type": "diversity",
        "params": {
          "field": "category",
          "max_same_category": 3
        }
      }
    ]
  }
}
```

---

### Pattern 2: Content Recommendation

```json
{
  "scene_id": "news_feed",
  "recall": {
    "modules": [
      {
        "name": "content_embedding",
        "type": "vector",
        "params": {
          "table": "article_embeddings",
          "topk": 500,
          "filters": {
            "publish_time": "last_7_days"
          }
        }
      },
      {
        "name": "hot_news",
        "type": "popular",
        "params": {
          "time_window_hours": 6,
          "topk": 100
        }
      }
    ]
  },
  "rank": {
    "modules": [
      {
        "name": "engagement_ranker",
        "type": "feature_based",
        "params": {
          "features": ["read_time", "comment_count", "share_count", "user_interest_match"],
          "model_endpoint": "http://eas/news_ranker"
        }
      }
    ]
  },
  "filter": {
    "rules": [
      {
        "name": "freshness_filter",
        "type": "threshold",
        "params": {
          "field": "publish_time",
          "min_value": "now-7d"
        }
      },
      {
        "name": "read_history_dedupe",
        "type": "bloom",
        "params": {
          "table": "user_read_history",
          "window_days": 30
        }
      }
    ]
  }
}
```

---

## Validation Checklists by Section

### Recall Configuration Validation

- [ ] All table references exist and are accessible
- [ ] Index types match table configurations
- [ ] topk values are reasonable (typically 50-1000)
- [ ] Timeout values appropriate (50-500ms)
- [ ] Filter conditions use valid fields
- [ ] Multiple modules have consistent merge strategy
- [ ] Weights sum to 1.0 (if weighted merge)

### Rank Configuration Validation

- [ ] Feature names match available features
- [ ] Feature tables accessible in target environment
- [ ] Model endpoints are reachable
- [ ] Batch sizes appropriate (20-100)
- [ ] Timeout accounts for batch processing
- [ ] Multi-stage ranking has proper topk cascade
- [ ] No circular dependencies

### Filter Configuration Validation

- [ ] Threshold values are reasonable
- [ ] Referenced fields exist
- [ ] Bloom filter tables accessible
- [ ] Custom rule syntax is valid
- [ ] Diversity constraints make sense
- [ ] Filter order is optimal (cheap filters first)

### Experiment Configuration Validation

- [ ] Traffic splits sum to 1.0
- [ ] Experiment IDs are unique
- [ ] Config overrides are syntactically valid
- [ ] Layer definitions don't conflict
- [ ] Experiment is enabled/disabled appropriately

---

## Common Configuration Issues

### Issue 1: Items Size Not Enough

**Error:**
```json
{
  "code": 299,
  "msg": "items size not enough"
}
```

**Possible Causes:**
1. Recall topk too low
2. Filters too aggressive
3. No data in recall tables
4. User has insufficient history

**Configuration Fix:**
```json
{
  "recall": {
    "modules": [
      {
        "topk": 500  // Increased from 100
      }
    ]
  },
  "filter": {
    "rules": [
      {
        "min_score": 0.05  // Lowered from 0.1
      }
    ]
  }
}
```

---

### Issue 2: Timeout Errors

**Error:**
```json
{
  "code": 500,
  "msg": "request timeout"
}
```

**Possible Causes:**
1. Recall timeout too low
2. Too many recall modules
3. Large batch size in ranking
4. Slow model endpoint

**Configuration Fix:**
```json
{
  "recall": {
    "modules": [
      {
        "params": {
          "timeout_ms": 500  // Increased from 200
        }
      }
    ]
  },
  "rank": {
    "modules": [
      {
        "params": {
          "batch_size": 30,  // Reduced from 100
          "timeout_ms": 200
        }
      }
    ]
  }
}
```

---

### Issue 3: Environment Mismatch

**Error:**
```
Resource 'prod_user_features' not found
```

**Cause:**
Using production table reference in Pre environment

**Configuration Fix:**
```json
{
  "rank": {
    "modules": [
      {
        "params": {
          "feature_tables": {
            "user_features": "pre_user_features_v1"  // Changed from prod_
          }
        }
      }
    ]
  }
}
```

---

## Best Practices

### 1. Naming Conventions

- Use descriptive module names: `user_embedding_recall`, not `recall1`
- Include version in table names: `user_profile_v2`
- Prefix tables by environment: `prod_`, `pre_`

### 2. Performance Optimization

- Set appropriate topk at each stage (cascade: 1000 → 200 → 50)
- Use cheap filters before expensive ones
- Batch model inference when possible
- Set reasonable timeouts (recall: 200-500ms, rank: 100-200ms)

### 3. Robustness

- Always include fallback recall (e.g., hot items)
- Set min/max constraints on values
- Handle missing features gracefully
- Use default values for optional parameters

### 4. Experimentation

- Start with small traffic splits (5%-10%)
- Keep baseline configuration stable
- Document experiment hypotheses
- Monitor key metrics

---

## Related Documentation

- [Verification Method](verification-method.md) - How to validate configurations
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
- [Related Commands](related-commands.md) - CLI commands for config management
