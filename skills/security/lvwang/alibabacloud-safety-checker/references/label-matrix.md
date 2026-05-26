# 完整标签配置矩阵

阿里云内容安全文本审核增强版支持 30 个细分标签，覆盖 7 个大类。

## 标签清单

### 色情类（3个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| pornographic_adult | 明确的色情描写、性行为相关内容 | 高 |
| sexual_terms | 性相关的术语和隐晦表达 | 中 |
| sexual_suggestive | 具有性暗示意味的擦边内容 | 中 |

### 涉政类（5个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| political_figure | 涉及敏感政治人物 | 高 |
| political_entity | 涉及政治敏感的组织机构、事件等 | 高 |
| political_n | 涉政负面言论 | 高 |
| political_p | 涉及禁止宣传的人物 | 高 |
| political_a | 涉及敏感地区相关话题 | 高 |

### 暴恐类（3个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| violent_extremist | 暴力极端主义、恐怖主义内容 | 高 |
| violent_incidents | 描述暴力事件、血腥场面 | 中 |
| violent_weapons | 武器制造、使用教唆等 | 中 |

### 违禁类（4个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| contraband_drug | 涉及毒品制造、贩卖、吸食 | 高 |
| contraband_gambling | 涉及赌博推广、赌博行为 | 中 |
| contraband_act | 其他违法违禁行为 | 中 |
| contraband_entity | 违禁物品描述和交易 | 中 |

### 不良内容类（6个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| inappropriate_discrimination | 种族、性别、地域等歧视性内容 | 中 |
| inappropriate_ethics | 违反社会公德和伦理道德 | 中 |
| inappropriate_profanity | 脏话、人身攻击、侮辱性语言 | 低 |
| inappropriate_oral | 低俗口语、粗鄙表达 | 低 |
| inappropriate_superstition | 宣扬封建迷信内容 | 低 |
| inappropriate_nonsense | 无意义的灌水、乱码内容 | 低 |

### 引流推广类（3个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| pt_to_sites | 引导跳转到外部网站 | 中 |
| pt_by_recruitment | 通过虚假招聘进行引流 | 中 |
| pt_to_contact | 留联系方式如QQ、微信、手机号进行引流 | 中 |

### 宗教类（5个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| religion_b | 涉及佛教敏感内容 | 中 |
| religion_t | 涉及道教敏感内容 | 中 |
| religion_c | 涉及基督教敏感内容 | 中 |
| religion_i | 涉及伊斯兰教敏感内容 | 高 |
| religion_h | 涉及印度教敏感内容 | 中 |

### 自定义类（1个）
| 标签Key | 说明 | 敏感度 |
|---------|------|--------|
| customized | 用户自定义的关键词和规则命中 | 自定义 |

## 各场景推荐配置

完整的场景标签配置请参阅 [scenarios.md](scenarios.md)。
