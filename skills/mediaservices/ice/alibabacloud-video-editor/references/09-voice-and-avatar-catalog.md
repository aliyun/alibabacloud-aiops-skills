# TTS Voice & Digital Avatar Catalog

Reference for choosing `Voice` values (used by `AI_TTS` and `AI_Avatar`) and `AvatarId` values (used by `AI_Avatar`). See `07-smart-media-features.md` for how to use these in a Timeline. Note `AI_Avatar` is a clip `Type` (placed directly in `VideoTrackClips`), not an entry in `Effects`.

- Traditional smart-dubbing voices: pass the voice value directly as `Voice` (e.g. `"Voice": "zhichu"`).
- CosyVoice voices (Alibaba Cloud Model Studio / Bailian): require the CosyVoice capability to be enabled separately on the Model Studio platform.
- Digital avatars: pass the `AvatarId` (e.g. `"AvatarId": "fanyu-broadcast_standing"`).
- **Cloned voices**: to reproduce a *specific* speaker (localizing a drama into another language while keeping the original actor's timbre), no catalog voice will do — pass an already-trained `VoiceId` as `customizedVoice` on the `AI_TTS` clip. Training the clone is **upstream's job, not this skill's**: ask the user for the `VoiceId` (`SKILL.md` §2.4). The voice works only inside ICE. Consumption pitfalls: `07-smart-media-features.md` (the `AI_TTS` subsections — ICE-only endpoint, `SpeechRate` silence, per-line micro-render).
- Multi-language coverage below is thin outside Chinese/English (one Spanish voice, no German). For a language the catalog does not cover, ask upstream for a cloned `VoiceId` or use a Model Studio TTS model directly.

## Traditional Smart Dubbing Voices

The API voice values below are the canonical identifiers; localized display names are omitted.

### Multi-Emotion (recommended)

Multi-emotion voices support per-sentence emotion control via the SSML `<emotion category="...">` tag (see `07-smart-media-features.md`). Each voice supports a different set of emotion categories.

| voice value | Type | Emotion categories |
| ------------- | ------ | -------------------- |
| zhimiao_emo | Multi-emotion female | serious, sad, disgust, jealousy, embarrassed, happy, fear, surprise, neutral, frustrated, affectionate, gentle, angry, newscast, customer-service, story, living |
| zhimi_emo | Friendly female | angry, fear, happy, hate, neutral, sad, surprise |
| zhibei_emo | Energetic child | neutral, happy, angry, sad, fear, hate, surprise |
| zhiyan_emo | Live-streaming female | neutral, happy, angry, sad, fear, hate, surprise, arousal |
| zhitian_emo | Sweet female | neutral, happy, angry, sad, fear, hate, surprise |

### Ultra-HD (recommended)

| voice value | Type |
| ------------- | ------ |
| zhitian | Sweet female |
| zhiqing | Taiwan-accent female |
| zhichu | Food-documentary male |
| zhide | Newscast male |
| zhifei | Passionate commentary |
| zhijia | Standard female |
| zhilun | Suspense commentary |
| zhinan | Advertising male |
| zhiqi | Gentle female |
| zhiqian | Information female |
| zhiru | Newscast female |
| zhiwei | Loli female |
| zhixiang | Magnetic male |

### Digital Human Voices

| voice value | Type |
| ------------- | ------ |
| abin | Cantonese-accent Mandarin |
| zhixiaobai | Mandarin female |
| zhixiaoxia | Mandarin female |

### Customer Service

| voice value | Type |
| ------------- | ------ |
| zhiya | Mandarin female |
| aixia | Friendly female |
| aiyue | Gentle female |
| aiya | Strict female |
| aijing | Strict female |
| aimei | Sweet female |
| siyue | Gentle female |
| aina | Zhejiang-accent female |
| aishuo | Natural male |
| aiyu | Natural female |
| xiaomei | Sweet female |
| yina | Zhejiang-accent female |
| sijing | Strict female |

### General

| voice value | Type |
| ------------- | ------ |
| zhiyuan | Mandarin female |
| zhiyue | Mandarin female |
| zhistella | Mandarin female |
| zhigui | Mandarin female |
| zhishuo | Mandarin male |
| zhida | Mandarin male |
| aiqi | Gentle female |
| aicheng | Standard male |
| aijia | Standard female |
| siqi | Gentle female |
| sijia | Standard female |
| mashu | Children's-drama male |
| yuer | Children's-drama female |
| ruoxi | Gentle female |
| aida | Standard male |
| sicheng | Standard male |
| ninger | Standard female |
| xiaoyun | Standard female |
| xiaogang | Standard male |
| ruilin | Standard female |

### Live Streaming

| voice value | Type |
| ------------- | ------ |
| zhimao | Mandarin female |
| laomei | Hawking female |
| laotie | Northeast buddy |
| xiaoxian | Friendly female |
| guijie | Friendly female |
| stella | Intellectual female |
| maoxiaomei | Energetic female |
| qiaowei | Store anchor |
| ailun | Suspense commentary |
| aifei | Passionate commentary |
| yaqun | Store broadcast |
| stanley | Steady male |
| kenny | Warm male |
| rosa | Natural female |

### Children

| voice value | Type |
| ------------- | ------ |
| aitong | Child voice |
| aiwei | Loli female |
| jielidou | Healing child |
| xiaobei | Loli female |
| sitong | Child voice |
| aibao | Loli female |

### Multi-Language

| voice value | Type |
| ------------- | ------ |
| perla | Italian female |
| camila | Spanish female |
| masha | Russian female |
| kyong | Korean female |
| tien | Vietnamese female |
| tomoka | Japanese female |
| tomoya | Japanese male |
| indah | Indonesian female |
| farah | Malay female |
| tala | Filipino female |

### English

| voice value | Type |
| ------------- | ------ |
| ava | American female |
| luca | British male |
| luna | British female |
| emily | British female |
| eric | British male |
| annie | American female |
| andy | American male |
| abby | American female |
| lydia | English-Chinese bilingual |
| olivia | British female |
| wendy | British female |
| harry | British male |

### Dialects

| voice value | Type |
| ------------- | ------ |
| cuijie | Northeast female |
| kelly | HK Cantonese female |
| jiajia | Cantonese female |
| dahu | Northeast male |
| aikan | Tianjin male |
| taozi | Cantonese female |
| qingqing | Taiwan-accent female |
| xiaoze | Hunan heavy accent |
| shanshan | Cantonese female |
| chuangirl | Sichuan female |

## Alibaba Cloud Model Studio Voices (CosyVoice)

CosyVoice is based on a generative speech large model; it predicts emotion, intonation and rhythm from context for more human-like results. It belongs to the Alibaba Cloud Model Studio (Bailian) platform and must be enabled there separately. CosyVoice currently covers all smart-dubbing scenarios of IMS (AI real-time interaction, batch video production official anchor voices, smart voice tasks, etc.).

When using CosyVoice voices, both a `model` parameter and a `voice` parameter are involved; default sample rate 22050 Hz, default format mp3.

### cosyvoice-v1

| voice parameter | Suitable scenarios | Language |
| ----------------- | -------------------- | ---------- |
| longwan | Voice assistant, navigation, chat digital human | Mandarin |
| longcheng | Voice assistant, navigation, chat digital human | Mandarin |
| longhua | Voice assistant, navigation, chat digital human | Mandarin |
| longxiaochun | Voice assistant, navigation, chat digital human | Chinese + English |
| longxiaoxia | Voice assistant, chat digital human | Chinese |
| longxiaocheng | Voice assistant, navigation, chat digital human | Chinese + English |
| longxiaobai | Chat digital human, audiobook, voice assistant | Chinese |
| longlaotie | Newscast, audiobook, voice assistant, live commerce, navigation | Northeast-accent Chinese |
| longshu | Audiobook, voice assistant, navigation, newscast, smart customer service | Chinese |
| longshuo | Voice assistant, navigation, newscast, customer service/collection | Chinese |
| longjing | Voice assistant, navigation, newscast, customer service/collection | Chinese |
| longmiao | Customer service/collection, navigation, audiobook, voice assistant | Chinese |
| longyue | Voice assistant, poetry recitation, audiobook reading, navigation, newscast, customer service/collection | Chinese |
| longyuan | Audiobook, voice assistant, chat digital human | Chinese |
| longfei | Meeting broadcast, newscast, audiobook | Chinese |
| longjielidou | Newscast, audiobook, chat assistant | Chinese + English |
| longtong | Audiobook, navigation, chat digital human | Chinese |
| longxiang | Newscast, audiobook, navigation | Chinese |
| loongstella | Voice assistant, live commerce, navigation, customer service/collection, audiobook | Chinese + English |
| loongbella | Voice assistant, customer service/collection, newscast, navigation | Chinese |

### cosyvoice-v2

> SSML restriction: `model="cosyvoice-v2"` voices support only `<speak>`, `<break>`, `<s>` and `<sub alias>`.

| voice parameter | Suitable scenarios | Language |
| ----------------- | -------------------- | ---------- |
| longcheng_v2 | Dubbed films | Chinese and mixed CN/EN |
| longhua_v2 | Smart customer service, newscast, chat, audiobook | Chinese and mixed CN/EN |
| longshu_v2 | Newscast, audiobook | Chinese and mixed CN/EN |
| loongbella_v2 | Smart customer service, newscast, chat, audiobook, car navigation | Chinese and mixed CN/EN |
| longwan_v2 | Smart customer service, newscast, chat, audiobook | Chinese and mixed CN/EN |
| longxiaochun_v2 | Smart customer service, newscast, chat, audiobook, car navigation | Chinese and mixed CN/EN |
| longxiaoxia_v2 | Smart customer service, newscast, chat, audiobook, car navigation | Chinese and mixed CN/EN |

## Digital Avatar Official Images (AvatarId)

Digital-human video synthesis tasks can be created via console or OpenAPI. Fixed output spec of the avatar synthesis: portrait 9:16, resolution 1080×1920, bitrate 4000 kb/s. When driving the avatar with speech or with text (converted to speech), the resulting speech must be **no shorter than 1 second**.

| AvatarId |
| ---------- |
| `fanyu-broadcast_standing` |
| `fanyu-marketing_standing` |
| `fanyu-sitting` |
| `fanyu` |
| `baihan-broadcast_standing` |
| `baihan-marketing_standing` |
| `baihan-sitting` |
| `baihan` |
| `boyuan-broadcast_standing` |
| `boyuan-marketing_standing` |
| `boyuan-sitting` |
| `boyuan` |
| `xinxin-broadcast_standing` |
| `xinxin-marketing_standing` |
| `xinxin-sitting` |
| `xinxin` |
| `robert_standing` |
| `sarah_standing` |
| `xiaoqu_business_sitting` |
| `xiaoqu_business_standing` |
| `xiaoqu_skirt_standing` |
| `xiaoqu_tshirt_standing` |
| `ziling_ancient_standing` |
| `ziling_dress_standing` |
| `ziling_skirt_standing` |

Example:

```json
{ "Type": "AI_Avatar", "AvatarId": "fanyu-broadcast_standing", "Voice": "zhichu", "Content": "Narration script" }
```

For narration script examples suitable for `Content` (story commentary / live commerce styles), see `10-narration-script-examples.md`.
