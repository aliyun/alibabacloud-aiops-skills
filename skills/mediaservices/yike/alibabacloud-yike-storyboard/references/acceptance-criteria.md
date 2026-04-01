# Acceptance Criteria - Yike Storyboard Skill

**Scenario**: Yike Storyboard Creation
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun ice ...
aliyun oss ...
```

#### ❌ INCORRECT
```bash
aliyun ICE ...      # Product name should be lowercase
```

### 2. Command — verify action exists under the product

#### ✅ CORRECT
```bash
aliyun ice create-yike-asset-upload
aliyun ice submit-yike-storyboard-job
aliyun ice get-yike-storyboard-job
aliyun oss cp
```

#### ❌ INCORRECT
```bash
aliyun ice CreateYikeAssetUpload     # Use kebab-case, not PascalCase
aliyun ice create_yike_asset_upload  # Use kebab-case, not snake_case
aliyun ice upload-novel              # This command doesn't exist
```

### 3. Parameters — verify each parameter name exists

#### ✅ CORRECT
```bash
aliyun ice create-yike-asset-upload --file-ext txt --file-type StoryboardInput
aliyun ice submit-yike-storyboard-job --file-url "..." --style-id Ghibli --narration-voice-id sys_GentleYoungMan
aliyun ice get-yike-storyboard-job --job-id xxx
aliyun oss cp --mode StsToken --access-key-id xxx --access-key-secret xxx --sts-token xxx
```

#### ❌ INCORRECT
```bash
aliyun ice create-yike-asset-upload --fileExt txt          # Use kebab-case
aliyun ice submit-yike-storyboard-job --FileURL "..."      # Use kebab-case
aliyun ice get-yike-storyboard-job --JobId xxx             # Use kebab-case
```

### 4. User-Agent — every command must include

#### ✅ CORRECT
```bash
aliyun ice create-yike-asset-upload --file-ext txt --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun ice create-yike-asset-upload --file-ext txt
# Missing --user-agent AlibabaCloud-Agent-Skills
```

### 5. Region — use correct region

#### ✅ CORRECT
```bash
aliyun ice create-yike-asset-upload --file-ext txt --region cn-shanghai
```

#### ❌ INCORRECT
```bash
aliyun ice create-yike-asset-upload --file-ext txt --region cn-hangzhou
# ICE service is only available in cn-shanghai region
```

---

## Parameter Value Validation

### Source Type — must be valid

#### ✅ CORRECT
```
Novel, Script
```

#### ❌ INCORRECT
```
novel, script           # Case sensitive
Story, Text, Document   # Invalid values
```

### Style ID — must be valid

#### ✅ CORRECT
```
RealisticPhotographyPro, RealisticGuzhuangPro, RealisticPhotography, 
RealisticGuzhuang, RealisticXianxia, RealisticEra, RealisticWasteland, 
GuofengAnime, GuofengAnime3D, Cartoon3D, Photorealistic3D, SciFiRealism, 
Chibi3D, ShojoManga, NewPeriodAnime, FairyTale2D, Wasteland2D, InkWuxia, 
ShadiaoMeme, Chibi2D, Ghibli, SciFiComic, AmericanSuperhero, Hokusei, 
RealisticComic, CinematicRealism, MinimalistRealism, ShonenManga
```

### Voice ID — must be valid

#### ✅ CORRECT
```
sys_ClassicMiddleAgedWoman, sys_ClassicYoungWoman, sys_IntellectualYoungWoman,
sys_GentleYoungMan, sys_WiseYoungMan, sys_ClassicYoungMan, sys_thoughtfulBoy,
sys_SereneIntellect, sys_RichBassMale, sys_CalmDeepMale, sys_MajesticBaritone,
sys_GravellySoulful, sys_SweetBrightGirl, sys_GracefulPoisedWoman, longbaizhi,
sys_YoungGracefulWoman, sys_MaturePoisedWoman, sys_MatureWiseWoman, sys_ElderlyWistfulWoman
```

### Aspect Ratio — must be valid

#### ✅ CORRECT
```
16:9, 9:16, 4:3, 3:4
```

### Resolution — must be valid

#### ✅ CORRECT
```
720P, 1K, 2K, 4K
```

### Shot Split Mode — must be valid

#### ✅ CORRECT
```
dialogue, firstPersonNarration, firstPersonNarrationPureVO, thirdPersonNarration
```

### Shot Split Mode Constraints

#### ✅ CORRECT
```bash
# Script can use dialogue mode
--source-type Script --shot-split-mode dialogue

# Novel can use narration modes
--source-type Novel --shot-split-mode firstPersonNarration
--source-type Novel --shot-split-mode thirdPersonNarration
```

#### ❌ INCORRECT
```bash
# Novel CANNOT use dialogue mode
--source-type Novel --shot-split-mode dialogue   # INVALID!
```

---

## Upload Script Validation

### upload_to_oss.sh — correct usage

#### ✅ CORRECT
```bash
bash scripts/upload_to_oss.sh novel.txt
bash scripts/upload_to_oss.sh /path/to/script.txt
```

#### ❌ INCORRECT
```bash
bash scripts/upload_to_oss.sh                    # Missing file argument
bash scripts/upload_to_oss.sh nonexistent.txt    # File must exist
```

---

## Job Status Validation

### Status Flow — expected sequence

#### ✅ CORRECT STATUS FLOW
```
Configuring/Parsing → Configuring/ParseSucc → Editing/Creating → Editing/CreateSucc
```

### Job Completion — success criteria

#### ✅ CORRECT
```json
{
  "JobStatus": "Succeeded",
  "JobResult": {
    "StoryboardInfoList": "[{\"storyboardId\":\"st_xxx\",\"status\":\"Produced\",\"subStatus\":\"ProduceSucc\"}]"
  }
}
```
