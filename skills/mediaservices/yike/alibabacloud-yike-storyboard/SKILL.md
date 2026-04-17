---
name: alibabacloud-yike-storyboard
description: |
  Yike Storyboard Creation Skill - Complete AI video creation workflow from novel/script to storyboard via conversational interface.
  Use this skill when users want to create storyboards, produce videos, convert novels/scripts to videos, or generate shot scripts.
  Trigger scenarios: "storyboard", "novel to video", "shot script", "script parsing", "video creation", "convert novel to video", "generate storyboard".
---

# Yike Storyboard Creation Skill

Help users complete the AI video creation workflow from novel/script to storyboard via conversational interface.

---

## Prerequisites

### 1. Aliyun CLI Check

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> 
> ```bash
> aliyun version
> ```
> 
> Verify version >= 3.3.3. If not installed or version is too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> 
> Then **[MUST]** run the following commands to configure CLI:
> ```bash
> # Enable auto plugin installation
> aliyun configure set --auto-plugin-install true
> 
> # Update plugins to latest
> aliyun plugin update
> 
> # Set region to cn-shanghai (required for ICE service)
> aliyun configure set --region cn-shanghai
> ```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard`

### 2. ICE Plugin Installation

> **Pre-check: ICE CLI Plugin required**
>
> ```bash
> aliyun plugin install --names ice
> ```
>
> Verify plugin is installed:
> ```bash
> aliyun ice --help
> ```

---

## Service Activation

### 1. Activate IMS (Intelligent Media Services)

> **Activation Link:** https://ice.console.aliyun.com/guide/default
>
> Log in with your Alibaba Cloud account and activate ICE Intelligent Media Services.

### 2. Log in to yikeai platform

> **Platform Link:** https://www.yikeai.com/#/home
>
> Visit the product website and authorize login with your Alibaba Cloud account.
> Currently Wanjing Yike is in invitation-only phase. Click [Apply for Access](https://survey.aliyun.com/apps/zhiliao/0FZ3TNiNP?spm=yikecom.4ad070b.0.0.53f53564Lny1lL) to submit your application.

---

## Credential Verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **DO NOT** read, print, or output AK/SK values
> - **ONLY USE** `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> 
> **If no valid profile exists, STOP and:**
> 1. Get credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Run `aliyun configure` to set up credentials

---

## RAM Permissions

This skill requires ICE permissions: `ice:CreateYikeAssetUpload`, `ice:SubmitYikeStoryboardJob`, `ice:GetYikeStoryboardJob`.

For complete permission policies, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Error Handling:** When any command fails due to permission errors, read `references/ram-policies.md` for required permissions.

---

## Parameter Confirmation

> **Confirm key parameters with user before file upload through natural dialogue.**

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| file_path | ✅ | Text file path (txt/docx, ≤5MB, ≤30K chars) | User provides |
| title | ✅ | Storyboard title | Extract from text |
| source-type | ✅ | `Novel` or `Script` | Based on content analysis |
| style | ✅ | Visual style ID | Based on genre |
| voice | ✅ | Narration voice ID | Based on protagonist |
| shot-split-mode | ✅ | Shot split mode | Based on narrative style |
| ratio | Optional | `16:9`, `9:16`, `4:3`, `3:4` | `9:16` |
| resolution | Optional | `720P`, `1K`, `2K`, `4K` | `720P` |

See [Task 0: Parameter Confirmation](#task-0-parameter-confirmation) for recommendation guide.

---

## Text Type Classification

| Type | Value | Description |
|------|-------|-------------|
| Novel | `Novel` | Primarily narrative, descriptive, psychological content for reading |
| Script | `Script` | Primarily scenes, dialogue, action descriptions for performance/filming |

**Classification Guide:**

Evaluate the following features to determine if text is novel or script (don't judge solely by dialogue presence - novels can have extensive dialogue too):

| Feature | Script | Novel |
|---------|--------|-------|
| Scene Markers | ✅ Has scene numbers, time, location, INT/EXT | ❌ No explicit scene markers |
| Structure | ✅ "Character Name + Dialogue" dominant | ❌ Narrative text dominant |
| Action Cues | ✅ Has stage directions, camera directions | ❌ No performable features |
| Literary Expression | ❌ Minimal | ✅ Rich environmental descriptions, psychology, emotions |

**Classification Rules:**

1. **Script**: Dominated by scenes, dialogue, action descriptions
2. **Novel**: Dominated by narration, description, psychological activity
3. **Mixed Content**: Determine dominant feature, output "more like script" or "more like novel"

> **Important**: After classification, confirm text type with user or let user specify directly.

---

## Core Workflow

### Task 0: Parameter Confirmation

Before upload, analyze the text and confirm key parameters with the user.

#### Step 1: Analyze Text Content

```bash
head -c 1000 <file_path>
```

Determine: genre, narrative style (first/third person), protagonist characteristics.

#### Step 2: Recommend & Confirm Parameters

Based on analysis, make recommendations and confirm with user through natural dialogue.

**Recommendation Guide:**

| Parameter | Based On | Examples |
|-----------|----------|----------|
| style | Genre | Modern Urban → `CinematicRealism`; Period Drama → `RealisticGuzhuangPro`; Fantasy → `RealisticXianxia`; Anime → `Ghibli` |
| voice | Protagonist | Young Female → `sys_ClassicYoungWoman`; Young Male → `sys_GentleYoungMan`; Mature Male → `sys_CalmDeepMale` |
| shot-split-mode | Narrative | Third person → `thirdPersonNarration`; First person → `firstPersonNarration`; Dialogue-heavy Script → `dialogue` |
| ratio | Platform | TikTok/Douyin → `9:16`; YouTube → `16:9` |
| resolution | Quality | Default `720P`; Higher quality `1K`/`2K`/`4K` |

**Defaults:** `9:16`, `720P` (vertical HD for mobile)

> **⚠️ Constraint:** `dialogue` mode is ONLY available for `Script` type, NOT for `Novel`.

**Example confirmation dialogue:**

> "Based on your modern urban romance novel, I recommend:
> - Style: `CinematicRealism` (film-quality, great for emotional scenes)
> - Voice: `sys_ClassicYoungWoman` (matches your young female protagonist)
> - Shot Mode: `thirdPersonNarration` (for third-person narrative)
> - Format: `9:16`, `720P` (vertical HD for mobile platforms)
> - Title: "雨夜归途"
>
> Does this look good, or would you like to change anything?"

If user has no preference, use recommended defaults. For full options, see [Style Mapping Table](#style-mapping-table) and [Voice Mapping Table](#narration-voice-mapping-table).

**DO NOT proceed to Task 1 until user confirms.**

---

### Task 1: Upload Text File to OSS

> **Prerequisite:** Task 0 (Parameter Confirmation) MUST be completed.

Use helper script to automatically get credentials and upload:

```bash
bash scripts/upload_to_oss.sh <file_path>
```

**Returns:** `FileURL` (for subsequent job submission)

### Task 2: Submit Storyboard Job

```bash
aliyun ice submit-yike-storyboard-job \
  --file-url "<FileURL>" \
  --source-type <SourceType> \
  --style-id <StyleId> \
  --narration-voice-id <VoiceId> \
  --aspect-ratio "9:16" \
  --resolution 720P \
  --shot-split-mode <ShotSplitMode> \
  --shot-prompt-mode multi \
  --video-model "wan2.6-r2v-flash" \
  --exec-mode StoryboardOnly \
  --title "<Title>" \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

> For complete parameter reference, see [references/related-commands.md](references/related-commands.md#3-submit-storyboard-job).

### Task 3: Query Job Status

```bash
aliyun ice get-yike-storyboard-job \
  --job-id <JobId> \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

> For complete parameter and response reference, see [references/related-commands.md](references/related-commands.md#4-query-job-status).

**Status Flow and User Prompts:**

| Status | SubStatus | Current Phase | User Prompt | Action |
|--------|-----------|---------------|-------------|--------|
| Configuring | Parsing | Entity Asset Parsing | "Parsing your script, AI is extracting characters, scenes and props..." | Wait |
| Configuring | ParseSucc | Entity Asset Image Generation | "Script parsed! Now generating images for characters, scenes and props. You can preview the progress here:" | **Provide Entity Management Link** |
| Editing | Creating | Shot Script Generation | "Entity assets ready! Now creating shot script, almost done..." | Wait |
| Editing | CreateSucc | Complete ✅ | "Shot script complete! You can now view and edit your storyboard:" | **Provide Editing Link** |
| Editing | CreateFailed | Failed ❌ | "Shot script generation failed, please check error message or resubmit." | Troubleshoot |

**Interactive Links:**

| Status | Link | Purpose |
|--------|------|---------|
| ParseSucc | `https://www.yikeai.com/#/storyboard/entitiesManagement?storyboardId={storyboardId}` | Preview entity assets (characters, scenes, props) generation progress |
| CreateSucc | `https://www.yikeai.com/#/storyboard/editing?storyboardId={storyboardId}` | Edit storyboard, generate videos, export final video |

**Job Status Description:**

| JobStatus | Description | User Prompt |
|-----------|-------------|-------------|
| Running | Job in progress | "Job is processing, usually takes a few minutes, please wait..." |
| Succeeded | Job succeeded | "Job completed!" |
| Failed | Job failed | "Job failed, please check error message." |
| Suspended | Job suspended | "Job suspended, some shots failed, can be manually fixed in storyboard." |

> **Query Recommendation**: Jobs usually take a few minutes. Recommend querying status every 30 seconds.

### Task 4: Get Storyboard Link

Get `storyboardId` from `JobResult.StoryboardInfoList` and construct link:

```
https://www.yikeai.com/#/storyboard/editing?storyboardId={storyboardId}
```

---

## Style Mapping Table

| StyleId | Name |
|---------|------|
| RealisticPhotographyPro | Realistic Photography Pro |
| RealisticGuzhuangPro | Realistic Chinese Period Pro |
| RealisticPhotography | Realistic Photography |
| RealisticGuzhuang | Realistic Chinese Period |
| RealisticXianxia | Realistic Xianxia |
| RealisticEra | Realistic Period |
| RealisticWasteland | Realistic Wasteland |
| GuofengAnime | 2D Chinese Style Anime |
| GuofengAnime3D | 3D Chinese Style Anime |
| Cartoon3D | 3D Cartoon |
| Photorealistic3D | Photorealistic 3D Render |
| SciFiRealism | Sci-Fi Realism |
| Chibi3D | 3D Chibi |
| ShojoManga | Shojo Manga |
| NewPeriodAnime | New Era Anime |
| FairyTale2D | 2D Fairy Tale |
| Wasteland2D | 2D Wasteland |
| InkWuxia | Ink Wuxia |
| ShadiaoMeme | Panda Meme Style |
| Chibi2D | 2D Chibi |
| Ghibli | Ghibli |
| SciFiComic | Cyberpunk |
| AmericanSuperhero | American Superhero |
| Hokusei | Hokusei |
| RealisticComic | Realistic Comic |
| CinematicRealism | Cinematic Realism |
| MinimalistRealism | Minimalist Realism |
| ShonenManga | Shonen Manga |

---

## Narration Voice Mapping Table

| Voice ID | Description |
|----------|-------------|
| sys_ClassicMiddleAgedWoman | Classic Female Narrator (25-45, wise) |
| sys_ClassicYoungWoman | Classic Young Female (18-25, intellectual) |
| sys_IntellectualYoungWoman | Intellectual Young Female (18-25, intellectual) |
| sys_GentleYoungMan | Gentle Young Male (18-25, gentle) |
| sys_WiseYoungMan | Wise Young Male (18-25, wise) |
| sys_ClassicYoungMan | Classic Young Male (18-25, charming) |
| sys_thoughtfulBoy | Thoughtful Boy (10-15, well-behaved) |
| sys_SereneIntellect | Serene Intellectual Male (18-25, cool and rational) |
| sys_RichBassMale | Rich Bass Male (18-25, deep voice) |
| sys_CalmDeepMale | Calm Deep Male (25-40, steady and deep) |
| sys_MajesticBaritone | Majestic Baritone (40-60, authoritative) |
| sys_GravellySoulful | Gravelly Soulful Male (40-60, weathered) |
| sys_SweetBrightGirl | Sweet Bright Girl (10-15, lively) |
| sys_GracefulPoisedWoman | Graceful Poised Woman (18-25, elegant) |
| longbaizhi | Long Baizhi (20-30, witty female narrator) |
| sys_YoungGracefulWoman | Young Graceful Woman (18-25, gentle) |
| sys_MaturePoisedWoman | Mature Poised Woman (25-40, graceful) |
| sys_MatureWiseWoman | Mature Wise Woman (25-40, elegant and wise) |
| sys_ElderlyWistfulWoman | Elderly Wistful Woman (40-60, nostalgic) |

---

## Shot Split Mode

| Mode | Description | Use Case | Supported Type |
|------|-------------|----------|----------------|
| dialogue | Dialogue Mode | Dialogue-heavy scripts, short dramas | Script only |
| firstPersonNarration | First Person Narration | Stories from protagonist's perspective, diary style | Novel/Script |
| firstPersonNarrationPureVO | First Person Pure VO | Inner monologue stories, prose | Novel/Script |
| thirdPersonNarration | Third Person Narration | Omniscient perspective stories, fairy tales, historical | Novel/Script |

> **Restriction**: When `source-type` is `Novel`, `dialogue` mode is **NOT supported**.

**Recommendation Guide:**

Choose appropriate mode based on text type and content analysis:

**Script:**
1. **High dialogue ratio** (short dramas, chat format, comedy) → Recommend `dialogue`
2. **First person narration** → Recommend `firstPersonNarration`
3. **Pure inner monologue/narration** (prose, reflections) → Recommend `firstPersonNarrationPureVO`
4. **Third person narration** → Recommend `thirdPersonNarration`

**Novel:**
1. **"I" perspective + has dialogue** (urban romance, mystery) → Recommend `firstPersonNarration`
2. **Pure inner monologue/narration** (prose, reflections) → Recommend `firstPersonNarrationPureVO`
3. **Third person narration** (fairy tales, mythology, history) → Recommend `thirdPersonNarration`

> **Important**: Before execution, describe mode features to user and let them confirm or choose.

---

## Capability Scope

**This skill automates:**
- Upload novel/script files to OSS
- Entity asset parsing (characters, scenes, props extraction)
- Entity asset image generation
- Shot script generation
- Job status tracking

**After shot script completion, continue in UI:**

Once the job reaches `CreateSucc` status, this skill's automation is complete. The following steps require the Yike Storyboard web interface:

1. **Edit shot script** - Adjust shot content, descriptions, and prompts
2. **Generate shot images/videos** - AI generates images/videos for each shot
3. **Edit and assemble** - Fine-tune timing, add transitions
4. **Export final video** - Render and download the complete video

> **Next Step**: Open the storyboard editing link and continue your video creation journey!

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI Installation Guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM Permission Policies |
| [references/related-commands.md](references/related-commands.md) | Related CLI Commands |
| [references/verification-method.md](references/verification-method.md) | Verification Methods |

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| MainAccountUserNotFound | Yike service not activated | Apply for access at [Service Activation](#2-log-in-to-yikeai-platform) section |
| InvalidAccessKeyId | Invalid AK/SK | Check credential configuration |
| Forbidden | Insufficient permissions | See RAM Permissions section |
| region can't be empty | OSS upload missing region | Add `--region cn-shanghai` |

> **Note**: If you receive `MainAccountUserNotFound` error, it means your account has not been whitelisted for the Yike service. Please visit https://www.yikeai.com and apply for access through the [invitation application form](https://survey.aliyun.com/apps/zhiliao/0FZ3TNiNP).
