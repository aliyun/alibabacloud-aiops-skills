"""
业务场景模板定义 - 为不同业务场景提供标签配置建议、测试方案和控制台操作指南

核心思路：
1. 内容安全控制台支持"复制Service"来为不同业务创建独立的审核策略
2. 每个Service可以独立开启/关闭具体的检测标签
3. 不同业务场景对内容的审核标准有显著差异
4. 本模块预定义场景模板，指导"先配后测"的工作流
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ============================================================
# 检测标签定义（国内版，30个细分标签）
# ============================================================

class LabelCategory(Enum):
    """标签大类"""
    PORNOGRAPHIC = "色情"
    POLITICAL = "涉政"
    VIOLENCE = "暴恐"
    CONTRABAND = "违禁"
    INAPPROPRIATE = "不良内容"
    PROMOTION = "引流推广"
    RELIGION = "宗教"
    CUSTOM = "自定义"


@dataclass
class DetectionLabel:
    """检测标签定义"""
    key: str                     # API返回的标签key
    name: str                    # 中文名称
    category: LabelCategory      # 所属大类
    description: str             # 描述说明


# 完整标签列表（国内版）
ALL_LABELS: List[DetectionLabel] = [
    # --- 色情类 ---
    DetectionLabel("pornographic_adult", "色情", LabelCategory.PORNOGRAPHIC,
                   "明确的色情描写、性行为相关内容"),
    DetectionLabel("sexual_terms", "性相关术语", LabelCategory.PORNOGRAPHIC,
                   "性相关的术语和隐晦表达"),
    DetectionLabel("sexual_suggestive", "性暗示", LabelCategory.PORNOGRAPHIC,
                   "具有性暗示意味的擦边内容"),

    # --- 涉政类 ---
    DetectionLabel("political_figure", "涉政人物", LabelCategory.POLITICAL,
                   "涉及敏感政治人物"),
    DetectionLabel("political_entity", "涉政实体", LabelCategory.POLITICAL,
                   "涉及政治敏感的组织机构、事件等"),
    DetectionLabel("political_n", "涉政负面", LabelCategory.POLITICAL,
                   "涉政负面言论"),
    DetectionLabel("political_p", "涉政禁宣人物", LabelCategory.POLITICAL,
                   "涉及禁止宣传的人物"),
    DetectionLabel("political_a", "涉政敏感地区", LabelCategory.POLITICAL,
                   "涉及敏感地区相关话题"),

    # --- 暴恐类 ---
    DetectionLabel("violent_extremist", "暴力极端", LabelCategory.VIOLENCE,
                   "暴力极端主义、恐怖主义内容"),
    DetectionLabel("violent_incidents", "暴力事件", LabelCategory.VIOLENCE,
                   "描述暴力事件、血腥场面"),
    DetectionLabel("violent_weapons", "武器相关", LabelCategory.VIOLENCE,
                   "武器制造、使用教唆等"),

    # --- 违禁类 ---
    DetectionLabel("contraband_drug", "毒品相关", LabelCategory.CONTRABAND,
                   "涉及毒品制造、贩卖、吸食"),
    DetectionLabel("contraband_gambling", "赌博相关", LabelCategory.CONTRABAND,
                   "涉及赌博推广、赌博行为"),
    DetectionLabel("contraband_act", "违禁行为", LabelCategory.CONTRABAND,
                   "其他违法违禁行为"),
    DetectionLabel("contraband_entity", "违禁物品", LabelCategory.CONTRABAND,
                   "违禁物品描述和交易"),

    # --- 不良内容类 ---
    DetectionLabel("inappropriate_discrimination", "歧视内容", LabelCategory.INAPPROPRIATE,
                   "种族、性别、地域等歧视性内容"),
    DetectionLabel("inappropriate_ethics", "违背公序良俗", LabelCategory.INAPPROPRIATE,
                   "违反社会公德和伦理道德"),
    DetectionLabel("inappropriate_profanity", "辱骂攻击", LabelCategory.INAPPROPRIATE,
                   "脏话、人身攻击、侮辱性语言"),
    DetectionLabel("inappropriate_oral", "低俗口语", LabelCategory.INAPPROPRIATE,
                   "低俗口语、粗鄙表达"),
    DetectionLabel("inappropriate_superstition", "封建迷信", LabelCategory.INAPPROPRIATE,
                   "宣扬封建迷信内容"),
    DetectionLabel("inappropriate_nonsense", "无意义灌水", LabelCategory.INAPPROPRIATE,
                   "无意义的灌水、乱码内容"),

    # --- 引流推广类 ---
    DetectionLabel("pt_to_sites", "站外引流", LabelCategory.PROMOTION,
                   "引导跳转到外部网站"),
    DetectionLabel("pt_by_recruitment", "招聘引流", LabelCategory.PROMOTION,
                   "通过虚假招聘进行引流"),
    DetectionLabel("pt_to_contact", "联系方式引流", LabelCategory.PROMOTION,
                   "留联系方式如QQ、微信、手机号进行引流"),

    # --- 宗教类 ---
    DetectionLabel("religion_b", "佛教相关", LabelCategory.RELIGION,
                   "涉及佛教敏感内容"),
    DetectionLabel("religion_t", "道教相关", LabelCategory.RELIGION,
                   "涉及道教敏感内容"),
    DetectionLabel("religion_c", "基督教相关", LabelCategory.RELIGION,
                   "涉及基督教敏感内容"),
    DetectionLabel("religion_i", "伊斯兰教相关", LabelCategory.RELIGION,
                   "涉及伊斯兰教敏感内容"),
    DetectionLabel("religion_h", "印度教相关", LabelCategory.RELIGION,
                   "涉及印度教敏感内容"),

    # --- 自定义 ---
    DetectionLabel("customized", "自定义规则", LabelCategory.CUSTOM,
                   "用户自定义的关键词和规则命中"),
]

# 构建标签快速查找表
LABEL_MAP: Dict[str, DetectionLabel] = {label.key: label for label in ALL_LABELS}


# ============================================================
# 标签开关状态定义
# ============================================================

class LabelSwitch(Enum):
    """标签建议状态"""
    ON = "开启"           # 建议开启
    OFF = "关闭"          # 建议关闭
    OPTIONAL = "可选"     # 根据具体业务需要决定
    CRITICAL = "必须开启"  # 强制要求开启（红线标签）


# ============================================================
# 业务场景定义
# ============================================================

@dataclass
class ScenarioTestPlan:
    """场景测试计划"""
    sample_categories: List[str]                    # 需要准备的样本分类
    sample_descriptions: Dict[str, str]             # 各分类的样本说明
    expected_outcomes: Dict[str, str]               # 预期测试结果
    focus_labels: List[str]                         # 重点关注的标签
    edge_cases: List[str]                           # 边界case描述


@dataclass
class BusinessScenario:
    """业务场景模板"""
    id: str                                         # 场景ID
    name: str                                       # 场景名称
    description: str                                # 场景描述
    industry: str                                   # 所属行业
    base_service: str                               # 基础service
    recommended_service_suffix: str                 # 建议的自定义service后缀

    # 标签配置矩阵: label_key → LabelSwitch
    label_config: Dict[str, LabelSwitch] = field(default_factory=dict)

    # 配置说明
    config_notes: List[str] = field(default_factory=list)

    # 场景特殊性说明
    special_requirements: List[str] = field(default_factory=list)

    # 关联的测试计划
    test_plan: Optional[ScenarioTestPlan] = None

    # 风险容忍度说明
    risk_tolerance: str = ""


# ============================================================
# 预定义业务场景模板
# ============================================================

def _build_ai_companion_chat() -> BusinessScenario:
    """AI陪聊/虚拟伴侣场景"""
    return BusinessScenario(
        id="ai_companion_chat",
        name="AI陪聊/虚拟伴侣",
        description="AI角色扮演、情感陪伴、虚拟恋人等场景。用户可能尝试诱导AI产生不当内容，"
                    "对色情擦边和情感操控的检测需求最高。",
        industry="AI应用",
        base_service="aigc_moderation_byllm",
        recommended_service_suffix="ai_companion",
        label_config={
            # 色情 - 全面严格
            "pornographic_adult": LabelSwitch.CRITICAL,
            "sexual_terms": LabelSwitch.CRITICAL,
            "sexual_suggestive": LabelSwitch.ON,
            # 涉政 - 开启核心项
            "political_figure": LabelSwitch.ON,
            "political_entity": LabelSwitch.ON,
            "political_n": LabelSwitch.ON,
            "political_p": LabelSwitch.ON,
            "political_a": LabelSwitch.OPTIONAL,
            # 暴恐 - 开启
            "violent_extremist": LabelSwitch.CRITICAL,
            "violent_incidents": LabelSwitch.ON,
            "violent_weapons": LabelSwitch.ON,
            # 违禁
            "contraband_drug": LabelSwitch.CRITICAL,
            "contraband_gambling": LabelSwitch.ON,
            "contraband_act": LabelSwitch.ON,
            "contraband_entity": LabelSwitch.ON,
            # 不良内容
            "inappropriate_discrimination": LabelSwitch.CRITICAL,
            "inappropriate_ethics": LabelSwitch.ON,
            "inappropriate_profanity": LabelSwitch.ON,
            "inappropriate_oral": LabelSwitch.OPTIONAL,  # 陪聊场景口语较多，太严会影响体验
            "inappropriate_superstition": LabelSwitch.OPTIONAL,
            "inappropriate_nonsense": LabelSwitch.OFF,  # AI回复不会灌水
            # 引流
            "pt_to_sites": LabelSwitch.ON,
            "pt_by_recruitment": LabelSwitch.OFF,
            "pt_to_contact": LabelSwitch.ON,
            # 宗教
            "religion_b": LabelSwitch.OPTIONAL,
            "religion_t": LabelSwitch.OPTIONAL,
            "religion_c": LabelSwitch.OPTIONAL,
            "religion_i": LabelSwitch.OPTIONAL,
            "religion_h": LabelSwitch.OPTIONAL,
            # 自定义
            "customized": LabelSwitch.ON,
        },
        config_notes=[
            "色情三标签必须全部开启，AI陪聊是色情擦边的高发场景",
            "sexual_suggestive建议开启，防止AI生成暗示性调情内容",
            "inappropriate_oral可视情况调整——过严会让AI对话风格僵硬",
            "inappropriate_nonsense建议关闭——AI生成内容不存在灌水场景",
            "建议配合PLUS服务的llm_query_moderation检测用户输入指令",
            "建议自定义关键词覆盖：角色扮演诱导、越狱提示词等",
        ],
        special_requirements=[
            "需同时检测用户输入(llm_query_moderation)和AI输出(llm_response_moderation)",
            "重点防范'越狱'(jailbreak)攻击，诱导AI脱离安全约束",
            "关注情感操控/PUA/自伤引导等新型风险",
            "角色扮演场景下，虚构情节中的暴力/色情描写需要区分对待",
        ],
        risk_tolerance="极低——色情/诱导/歧视零容忍，口语/情绪表达适当宽松",
        test_plan=ScenarioTestPlan(
            sample_categories=[
                "normal_chat", "sexual_explicit", "sexual_suggestive",
                "jailbreak_prompt", "emotional_manipulation", "self_harm_guidance",
                "role_play_boundary", "political_sensitive", "violence_describe",
            ],
            sample_descriptions={
                "normal_chat": "正常的情感交流、日常对话",
                "sexual_explicit": "明确的色情对话内容",
                "sexual_suggestive": "暧昧擦边、性暗示的对话",
                "jailbreak_prompt": "越狱攻击提示词（DAN/忽略指令等）",
                "emotional_manipulation": "情感操控/PUA话术",
                "self_harm_guidance": "引导自伤/自杀的对话",
                "role_play_boundary": "角色扮演中的边界测试内容",
                "political_sensitive": "借角色之口讨论政治敏感话题",
                "violence_describe": "虚构故事中的暴力描写",
            },
            expected_outcomes={
                "normal_chat": "none - 应全部通过",
                "sexual_explicit": "high - 应全部拦截",
                "sexual_suggestive": "medium/high - 大部分应识别",
                "jailbreak_prompt": "high - 应被识别为攻击指令",
                "emotional_manipulation": "medium/high - 应被标记",
                "self_harm_guidance": "high - 必须拦截",
                "role_play_boundary": "需人工判断 - 测试策略边界",
                "political_sensitive": "high - 应被拦截",
                "violence_describe": "medium - 区分虚构与真实暴力",
            },
            focus_labels=[
                "pornographic_adult", "sexual_terms", "sexual_suggestive",
                "inappropriate_ethics", "violent_incidents",
            ],
            edge_cases=[
                "正常的亲密关系对话 vs 色情内容的边界",
                "文学性质的情感描写 vs 色情擦边",
                "角色扮演中的虚构暴力 vs 真实暴力教唆",
                "用户情绪低落时的正常倾诉 vs 自伤风险对话",
                "越狱攻击变体（编码/拆字/多语言混合）",
            ],
        ),
    )


def _build_game_chat() -> BusinessScenario:
    """游戏聊天室场景"""
    return BusinessScenario(
        id="game_chat",
        name="游戏聊天室",
        description="游戏内公聊、组队频道、世界频道等场景。玩家对话节奏快、口语化重、"
                    "竞技场景下粗口频率高，需要在游戏体验和合规之间找平衡。",
        industry="游戏",
        base_service="ugc_moderation_byllm",
        recommended_service_suffix="game_chat",
        label_config={
            # 色情 - 严格
            "pornographic_adult": LabelSwitch.CRITICAL,
            "sexual_terms": LabelSwitch.ON,
            "sexual_suggestive": LabelSwitch.OPTIONAL,  # 游戏语境下部分表达可接受
            # 涉政 - 核心开启
            "political_figure": LabelSwitch.ON,
            "political_entity": LabelSwitch.ON,
            "political_n": LabelSwitch.ON,
            "political_p": LabelSwitch.ON,
            "political_a": LabelSwitch.OPTIONAL,
            # 暴恐 - 需区分游戏暴力
            "violent_extremist": LabelSwitch.CRITICAL,
            "violent_incidents": LabelSwitch.OPTIONAL,  # 游戏场景本身涉及战斗
            "violent_weapons": LabelSwitch.OPTIONAL,  # 游戏中武器讨论属正常
            # 违禁
            "contraband_drug": LabelSwitch.ON,
            "contraband_gambling": LabelSwitch.ON,  # 游戏代练/RMT可能涉及
            "contraband_act": LabelSwitch.ON,
            "contraband_entity": LabelSwitch.OPTIONAL,
            # 不良内容
            "inappropriate_discrimination": LabelSwitch.CRITICAL,
            "inappropriate_ethics": LabelSwitch.ON,
            "inappropriate_profanity": LabelSwitch.ON,  # 开启但阈值可调高
            "inappropriate_oral": LabelSwitch.OFF,  # 游戏口语化重，关闭避免大量误判
            "inappropriate_superstition": LabelSwitch.OFF,  # 游戏常有玄幻/魔法元素
            "inappropriate_nonsense": LabelSwitch.ON,  # 防刷屏
            # 引流
            "pt_to_sites": LabelSwitch.CRITICAL,  # 外挂/代练网站引流
            "pt_by_recruitment": LabelSwitch.ON,
            "pt_to_contact": LabelSwitch.ON,  # 私下交易引流
            # 宗教
            "religion_b": LabelSwitch.OFF,
            "religion_t": LabelSwitch.OFF,
            "religion_c": LabelSwitch.OFF,
            "religion_i": LabelSwitch.OFF,
            "religion_h": LabelSwitch.OFF,
            # 自定义
            "customized": LabelSwitch.ON,
        },
        config_notes=[
            "violent_incidents/violent_weapons建议设为可选——游戏本身有战斗场景，完全开启会大量误判",
            "inappropriate_oral建议关闭——游戏聊天口语化极重，开启会严重影响正常交流",
            "inappropriate_superstition建议关闭——仙侠/魔幻类游戏中修仙/法术是正常用语",
            "inappropriate_nonsense建议开启——防止聊天频道被刷屏广告",
            "pt_to_sites务必开启——游戏外挂/代练/黑产是重灾区",
            "宗教类标签建议关闭——游戏中大量涉及神话/宗教元素属于世界观设定",
            "建议自定义关键词覆盖：外挂名称、代练广告、RMT交易术语",
        ],
        special_requirements=[
            "游戏场景需区分'游戏内暴力描写'和'现实暴力威胁'",
            "竞技游戏中适度的对抗性语言可能被误判为辱骂",
            "需建立游戏专属词库：外挂名、黑话、缩写",
            "消息频率高、长度短，批量审核性能要求高",
        ],
        risk_tolerance="中等——红线内容零容忍，口语/游戏术语/虚拟暴力适当宽松",
        test_plan=ScenarioTestPlan(
            sample_categories=[
                "normal_game_chat", "trash_talk", "real_threat",
                "cheat_ad", "rmt_trade", "sexual_content",
                "game_violence_discuss", "political_in_game",
            ],
            sample_descriptions={
                "normal_game_chat": "正常的游戏交流、组队邀请、策略讨论",
                "trash_talk": "竞技场景下的垃圾话/挑衅（游戏文化一部分）",
                "real_threat": "超出游戏范围的真实人身威胁",
                "cheat_ad": "外挂/辅助工具广告",
                "rmt_trade": "RMT现金交易/代练广告",
                "sexual_content": "聊天室中的色情骚扰",
                "game_violence_discuss": "游戏内战斗/杀戮的正常讨论",
                "political_in_game": "借游戏聊天讨论现实政治",
            },
            expected_outcomes={
                "normal_game_chat": "none - 应全部通过",
                "trash_talk": "需人工判断 - 测试策略边界（适度应放行）",
                "real_threat": "high - 必须拦截",
                "cheat_ad": "high - 应被引流标签捕获",
                "rmt_trade": "high - 应被引流/违禁标签捕获",
                "sexual_content": "high - 应拦截",
                "game_violence_discuss": "none/low - 不应过度拦截",
                "political_in_game": "high - 应被拦截",
            },
            focus_labels=[
                "inappropriate_profanity", "pt_to_sites", "pt_to_contact",
                "violent_incidents", "contraband_gambling",
            ],
            edge_cases=[
                "竞技垃圾话 vs 真实辱骂的边界",
                "游戏内杀怪讨论 vs 真实暴力描述",
                "游戏道具交易 vs RMT黑产交易",
                "游戏角色名 vs 现实涉政人物名",
                "游戏世界观中的宗教元素 vs 真实宗教敏感",
            ],
        ),
    )


def _build_general_chat() -> BusinessScenario:
    """通用Chat/社交场景"""
    return BusinessScenario(
        id="general_chat",
        name="通用Chat/社交聊天",
        description="即时通讯IM、社交平台私聊/群聊、论坛回帖等通用UGC场景。"
                    "内容类型多样，需要全面覆盖各类风险。",
        industry="社交/IM",
        base_service="ugc_moderation_byllm_pro",
        recommended_service_suffix="general_chat",
        label_config={
            # 色情 - 严格
            "pornographic_adult": LabelSwitch.CRITICAL,
            "sexual_terms": LabelSwitch.CRITICAL,
            "sexual_suggestive": LabelSwitch.ON,
            # 涉政 - 全面开启
            "political_figure": LabelSwitch.CRITICAL,
            "political_entity": LabelSwitch.CRITICAL,
            "political_n": LabelSwitch.CRITICAL,
            "political_p": LabelSwitch.CRITICAL,
            "political_a": LabelSwitch.ON,
            # 暴恐 - 全面开启
            "violent_extremist": LabelSwitch.CRITICAL,
            "violent_incidents": LabelSwitch.ON,
            "violent_weapons": LabelSwitch.ON,
            # 违禁 - 全面开启
            "contraband_drug": LabelSwitch.CRITICAL,
            "contraband_gambling": LabelSwitch.ON,
            "contraband_act": LabelSwitch.ON,
            "contraband_entity": LabelSwitch.ON,
            # 不良内容
            "inappropriate_discrimination": LabelSwitch.CRITICAL,
            "inappropriate_ethics": LabelSwitch.ON,
            "inappropriate_profanity": LabelSwitch.ON,
            "inappropriate_oral": LabelSwitch.ON,
            "inappropriate_superstition": LabelSwitch.OPTIONAL,
            "inappropriate_nonsense": LabelSwitch.ON,
            # 引流
            "pt_to_sites": LabelSwitch.CRITICAL,
            "pt_by_recruitment": LabelSwitch.ON,
            "pt_to_contact": LabelSwitch.ON,
            # 宗教
            "religion_b": LabelSwitch.OPTIONAL,
            "religion_t": LabelSwitch.OPTIONAL,
            "religion_c": LabelSwitch.OPTIONAL,
            "religion_i": LabelSwitch.OPTIONAL,
            "religion_h": LabelSwitch.OPTIONAL,
            # 自定义
            "customized": LabelSwitch.ON,
        },
        config_notes=[
            "社交场景需最全面的标签覆盖，建议使用ugc_moderation_byllm_pro",
            "涉政全系列标签建议设为必须开启——社交平台是涉政内容的高风险场景",
            "inappropriate_oral建议开启——社交场景中口语化脏话需要治理",
            "引流三标签全部开启——微商/诈骗/色情引流是社交平台顽疾",
            "宗教类按业务所在地区和平台调性决定是否开启",
        ],
        special_requirements=[
            "用户量大、内容类型多样，需要高召回+可接受的误判率",
            "私聊和群聊可能需要不同的审核策略",
            "需关注用户间的骚扰、跟踪、威胁行为",
            "需关注未成年人保护相关内容",
        ],
        risk_tolerance="低——全面覆盖，宁可误判不可漏判，通过人工复审降低误判影响",
        test_plan=ScenarioTestPlan(
            sample_categories=[
                "normal_social", "spam_ad", "sexual_harassment",
                "political_discuss", "violence_threat", "fraud_scam",
                "minor_protection", "drug_trade", "gambling_promo",
            ],
            sample_descriptions={
                "normal_social": "正常的社交聊天、生活分享",
                "spam_ad": "垃圾广告、营销信息",
                "sexual_harassment": "性骚扰、跟踪纠缠",
                "political_discuss": "涉政敏感话题讨论",
                "violence_threat": "人身威胁、恐吓信息",
                "fraud_scam": "诈骗话术、钓鱼引流",
                "minor_protection": "针对未成年人的不当内容",
                "drug_trade": "涉毒暗语/交易信息",
                "gambling_promo": "赌博推广信息",
            },
            expected_outcomes={
                "normal_social": "none - 应全部通过",
                "spam_ad": "high - 应被引流标签捕获",
                "sexual_harassment": "high - 应被色情/不当标签捕获",
                "political_discuss": "medium/high - 视内容具体程度",
                "violence_threat": "high - 必须拦截",
                "fraud_scam": "high - 应被引流/违禁标签捕获",
                "minor_protection": "high - 必须拦截",
                "drug_trade": "high - 应被违禁标签捕获",
                "gambling_promo": "high - 应被违禁标签捕获",
            },
            focus_labels=[
                "political_figure", "political_entity", "political_n",
                "pornographic_adult", "pt_to_sites", "pt_to_contact",
                "inappropriate_profanity", "violent_extremist",
            ],
            edge_cases=[
                "正常新闻讨论 vs 涉政敏感言论",
                "亲密关系私聊 vs 色情骚扰",
                "正当商业推广 vs 引流广告",
                "网络缩写/谐音 vs 真实脏话",
                "文学/影视讨论中的暴力描写",
            ],
        ),
    )


def _build_ecommerce() -> BusinessScenario:
    """零售电商场景"""
    return BusinessScenario(
        id="ecommerce",
        name="零售电商",
        description="商品评价、商品描述、客服对话、直播带货文案等电商场景。"
                    "重点关注虚假宣传、违禁品、引流竞品等商业风险。",
        industry="电商/零售",
        base_service="ugc_moderation_byllm",
        recommended_service_suffix="ecommerce",
        label_config={
            # 色情 - 开启核心项
            "pornographic_adult": LabelSwitch.CRITICAL,
            "sexual_terms": LabelSwitch.ON,
            "sexual_suggestive": LabelSwitch.OPTIONAL,  # 部分服饰/内衣类目需宽松
            # 涉政
            "political_figure": LabelSwitch.ON,
            "political_entity": LabelSwitch.ON,
            "political_n": LabelSwitch.ON,
            "political_p": LabelSwitch.ON,
            "political_a": LabelSwitch.OPTIONAL,
            # 暴恐
            "violent_extremist": LabelSwitch.CRITICAL,
            "violent_incidents": LabelSwitch.OPTIONAL,
            "violent_weapons": LabelSwitch.ON,  # 管制刀具/仿真枪等
            # 违禁 - 电商重点
            "contraband_drug": LabelSwitch.CRITICAL,  # 药品/保健品违规宣传
            "contraband_gambling": LabelSwitch.ON,
            "contraband_act": LabelSwitch.CRITICAL,  # 假冒伪劣、违法经营
            "contraband_entity": LabelSwitch.CRITICAL,  # 违禁商品
            # 不良内容
            "inappropriate_discrimination": LabelSwitch.ON,
            "inappropriate_ethics": LabelSwitch.ON,
            "inappropriate_profanity": LabelSwitch.ON,  # 恶意差评中的辱骂
            "inappropriate_oral": LabelSwitch.OFF,  # 评价口语化正常
            "inappropriate_superstition": LabelSwitch.ON,  # 虚假功效宣传
            "inappropriate_nonsense": LabelSwitch.ON,  # 刷单好评检测
            # 引流 - 电商核心
            "pt_to_sites": LabelSwitch.CRITICAL,  # 跳转竞品/外部平台
            "pt_by_recruitment": LabelSwitch.ON,  # 招代理
            "pt_to_contact": LabelSwitch.CRITICAL,  # 绕过平台私下交易
            # 宗教
            "religion_b": LabelSwitch.OFF,
            "religion_t": LabelSwitch.OFF,
            "religion_c": LabelSwitch.OFF,
            "religion_i": LabelSwitch.OFF,
            "religion_h": LabelSwitch.OFF,
            # 自定义
            "customized": LabelSwitch.ON,
        },
        config_notes=[
            "违禁类标签是电商场景的重中之重——违禁商品、假冒伪劣必须严格拦截",
            "引流类标签必须全面开启——防止商家引导用户跳出平台交易",
            "sexual_suggestive视类目调整——内衣/泳装类目需适当宽松",
            "violent_weapons需开启——管制刀具、仿真枪等是电商违禁品",
            "inappropriate_superstition建议开启——'祖传秘方'等虚假功效宣传",
            "inappropriate_nonsense开启可辅助检测刷单好评/水军",
            "宗教类一般关闭——除非售卖宗教用品的专门类目",
            "建议自定义关键词覆盖：违禁品别名、竞品引流话术、虚假功效词",
        ],
        special_requirements=[
            "需区分商品描述和用户评价的不同审核标准",
            "直播场景需要实时性更高的审核能力",
            "关注《广告法》绝对化用语：最好、第一、国家级等",
            "需关注商品图片+文字的组合风险",
        ],
        risk_tolerance="中低——违禁品/引流零容忍，商品描述适度宽松，用户评价允许适当负面",
        test_plan=ScenarioTestPlan(
            sample_categories=[
                "normal_review", "fake_review", "product_desc_normal",
                "prohibited_goods", "false_advertising", "competitor_redirect",
                "contact_info_leak", "abusive_review", "drug_supplement",
            ],
            sample_descriptions={
                "normal_review": "正常的商品评价（好评/中评/差评）",
                "fake_review": "刷单/水军好评、模板化评价",
                "product_desc_normal": "正常的商品标题和描述",
                "prohibited_goods": "违禁商品（管制刀具/烟草/仿品等）描述",
                "false_advertising": "虚假宣传（绝对化用语/虚假功效）",
                "competitor_redirect": "引导跳转竞品/外部平台的话术",
                "contact_info_leak": "留联系方式绕过平台的信息",
                "abusive_review": "带人身攻击的恶意差评",
                "drug_supplement": "药品/保健品违规宣传",
            },
            expected_outcomes={
                "normal_review": "none - 应全部通过（包括合理差评）",
                "fake_review": "medium - 可检测但非强制拦截",
                "product_desc_normal": "none - 应全部通过",
                "prohibited_goods": "high - 必须拦截",
                "false_advertising": "medium/high - 应被识别",
                "competitor_redirect": "high - 应被引流标签捕获",
                "contact_info_leak": "high - 应被引流标签捕获",
                "abusive_review": "high - 应被辱骂标签捕获",
                "drug_supplement": "high - 应被违禁标签捕获",
            },
            focus_labels=[
                "contraband_entity", "contraband_act", "contraband_drug",
                "pt_to_sites", "pt_to_contact", "inappropriate_profanity",
            ],
            edge_cases=[
                "合理差评 vs 恶意攻击商家",
                "正常商品特性描述 vs 虚假功效宣传",
                "售后联系方式 vs 绕平台交易引流",
                "正常品牌名 vs 仿冒名牌",
                "内衣/泳装正常展示 vs 色情擦边",
            ],
        ),
    )


def _build_news_content() -> BusinessScenario:
    """资讯/新闻内容场景"""
    return BusinessScenario(
        id="news_content",
        name="资讯/新闻/自媒体",
        description="新闻资讯平台、自媒体文章、内容社区等PGC/PUGC场景。"
                    "内容较长、有新闻属性，涉政检测最为关键。",
        industry="资讯/媒体",
        base_service="ugc_moderation_byllm_pro",
        recommended_service_suffix="news_content",
        label_config={
            # 色情
            "pornographic_adult": LabelSwitch.CRITICAL,
            "sexual_terms": LabelSwitch.ON,
            "sexual_suggestive": LabelSwitch.ON,
            # 涉政 - 最严格
            "political_figure": LabelSwitch.CRITICAL,
            "political_entity": LabelSwitch.CRITICAL,
            "political_n": LabelSwitch.CRITICAL,
            "political_p": LabelSwitch.CRITICAL,
            "political_a": LabelSwitch.CRITICAL,
            # 暴恐
            "violent_extremist": LabelSwitch.CRITICAL,
            "violent_incidents": LabelSwitch.ON,
            "violent_weapons": LabelSwitch.ON,
            # 违禁
            "contraband_drug": LabelSwitch.ON,
            "contraband_gambling": LabelSwitch.ON,
            "contraband_act": LabelSwitch.ON,
            "contraband_entity": LabelSwitch.ON,
            # 不良内容
            "inappropriate_discrimination": LabelSwitch.CRITICAL,
            "inappropriate_ethics": LabelSwitch.ON,
            "inappropriate_profanity": LabelSwitch.ON,
            "inappropriate_oral": LabelSwitch.OPTIONAL,
            "inappropriate_superstition": LabelSwitch.ON,
            "inappropriate_nonsense": LabelSwitch.ON,
            # 引流
            "pt_to_sites": LabelSwitch.ON,
            "pt_by_recruitment": LabelSwitch.ON,
            "pt_to_contact": LabelSwitch.ON,
            # 宗教
            "religion_b": LabelSwitch.ON,
            "religion_t": LabelSwitch.ON,
            "religion_c": LabelSwitch.ON,
            "religion_i": LabelSwitch.ON,
            "religion_h": LabelSwitch.ON,
            # 自定义
            "customized": LabelSwitch.ON,
        },
        config_notes=[
            "涉政全系列标签必须全面开启且为最高优先级——新闻场景涉政风险最高",
            "宗教类标签建议全部开启——资讯内容涉及宗教话题需要严格审核",
            "需注意区分新闻报道本身 vs 用户评论——报道引述和评论的标准不同",
            "建议配合人工审核机制，机审标记+人工复核",
        ],
        special_requirements=[
            "新闻内容有时效性，审核需要快速响应",
            "新闻引述和评论观点需区别对待",
            "标题党/震惊体也是需要关注的风险",
            "历史事件叙述 vs 涉政敏感的边界较难把握",
        ],
        risk_tolerance="极低——涉政/宗教/歧视零容忍，新闻报道中的事实引述需区分",
    )


# ============================================================
# 场景注册表
# ============================================================

SCENARIO_REGISTRY: Dict[str, BusinessScenario] = {}


def _register_all():
    """注册所有预定义场景"""
    scenarios = [
        _build_ai_companion_chat(),
        _build_game_chat(),
        _build_general_chat(),
        _build_ecommerce(),
        _build_news_content(),
    ]
    for s in scenarios:
        SCENARIO_REGISTRY[s.id] = s


_register_all()


def get_scenario(scenario_id: str) -> Optional[BusinessScenario]:
    """获取指定场景模板"""
    return SCENARIO_REGISTRY.get(scenario_id)


def list_scenarios() -> List[BusinessScenario]:
    """列出所有场景"""
    return list(SCENARIO_REGISTRY.values())


def register_custom_scenario(scenario: BusinessScenario):
    """注册自定义场景"""
    SCENARIO_REGISTRY[scenario.id] = scenario
