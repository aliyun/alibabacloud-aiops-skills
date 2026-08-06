---
name: alibabacloud-video-prompt-architect
description: |
  Generates structured, high-quality prompts for AI video and image generation models.
  Transforms natural language descriptions into optimized prompts adapted for 18 models including Happy Horse, Seedance, Kling, Pika, Midjourney, Recraft, FLUX, and more.
  Use when creating video prompts, image prompts, product images, posters, or adapting prompts across different AI generation models.
  Triggers: "生成视频提示词", "视频prompt", "文生视频", "图生视频", "文生图", "商品图", "海报生成", "AI生成提示词", "prompt architect", "media prompt"
---

# AI Media Generation Prompt Architect

Automatically decompose a user's natural language request and generate high-quality structured prompts adapted for different AI models.

## Applicable Scenarios

- Users without prompt experience can quickly generate professional-level prompts
- Enterprise operations, design, and short-video teams for batch content production
- Unified prompt generation entry point for AI creation platforms
- Cross-platform multi-model creative adaptation

## Architecture

```
User natural language input → Intent analysis → Structured decomposition → Mode adaptation → Self-review reflection → Output high-quality Prompt
```

Components: `Intent Parsing Engine` + `Structured Prompt Generator` + `Multi-Mode Adapter` + `Negative Prompt Generator` + `Quality Self-Checker`

---

## Core Workflow

### 1. Receive User Input

Accept the user's natural language description, which can be a brief sentence, e.g.:
- "A girl dancing under cherry blossom trees"
- "A high-tech smartphone product showcase"
- "A romantic wedding photo at sunset by the sea"

### 2. Intent Analysis and Generation Mode Determination

Based on user input, automatically determine the most suitable generation mode and select the target model according to user specification or default strategy:

#### Task Type Identification

| Trigger Keywords | Generation Mode | Default Model |
|------------------|-----------------|---------------|
| Video, animation, motion, dynamic, clip | Text-to-Video | Happy Horse |
| Reference image, multi-character, image fusion video | Reference-to-Video | Happy Horse r2v |
| First frame, image-to-video, animate image | Image-to-Video | Happy Horse i2v |
| Image, photo, illustration, wallpaper, concept art | Text-to-Image | Nano Banana |
| Product, merchandise, e-commerce, showcase | Product Image Generation | seedream |
| Poster, promotion, advertisement, banner | Poster Generation | Midjourney |

#### Supported Video Generation Models

| Model | Use Case | Language | Prompt Style |
|-------|----------|----------|--------------|
| **Happy Horse** | Business custom videos, platform integration, lightweight creativity | **Chinese (mandatory)** | Structured Chinese, camera terms directly usable |
| **Seedance** | Short videos, narrative segments, motion shots | **Chinese (mandatory)** | Structured Chinese: subject + action + scene + camera + style |
| **Kling** | Cinematic videos, ads, drama segments | **Chinese (mandatory)** | Structured Chinese, emphasizing camera movement and visual texture |
| **Wanx** | Chinese-native video, general content, marketing videos | **Chinese (mandatory)** | Chinese structure, reduce abstract words |
| **Veo** | High-quality video, commercials, cinematic visuals | English | Complete description, emphasizing atmosphere, rhythm, scene details |
| **Sora** | Complex narratives, multi-character, physical consistency | English | Semantically coherent, clear subject relationships and action logic |
| **Hailuo** | Short videos, social content, quick production | **Chinese (mandatory)** | Concise and direct, emphasizing action, emotion, and style |
| **Runway** | Creative ads, brand content, stylized videos | English | Natural language + style directives, emphasizing brand consistency and visual style |
| **Pika** | Social media shorts, creative effects videos, viral content | English | Concise and dynamic, emphasizing creative transitions and special effects (melt/inflate/explode/crumble) |

#### Supported Image Generation Models

| Model | Use Case | Language | Prompt Style |
|-------|----------|----------|--------------|
| **Nano Banana** | Quick image generation, creative exploration, lightweight visuals | English | Concise and efficient: subject + style + composition |
| **GPT Image** | General images, design sketches, marketing graphics | English | Natural language, semantically clear |
| **Grok Image** | Creative images, social media visuals, personalized graphics | English | Natural description, emphasizing effects and themes |
| **seedream** | Commercial images, posters, high-quality pictures | **Chinese (mandatory)** | Structured Chinese: subject + scene + lighting + texture + composition |
| **Qwen Image** | Chinese design needs, general images, marketing visuals | **Chinese (mandatory)** | Chinese-organized, emphasizing purpose and style |
| **Midjourney** | Posters, concept art, stylized illustrations | English | Style + composition + material + lighting keyword combinations |
| **FLUX** | API integration, developer workflows, self-hosted | English | Structured English: subject + scene + style + quality, precise control |
| **Ideogram** | Posters/ads/covers, text rendering, typographic images | English | Natural language + text content directives, emphasizing layout and readability |
| **Recraft** | Vector graphics, brand design, icons/logos, print materials | English | Design-oriented: subject + style + color palette + output format, supports SVG/EPS vector output |

> If the user does not specify a model, use the default model based on task type. Users can switch at any time.
> For detailed model adaptation rules, see `references/generation-modes.md`

### 3. Structured Prompt Generation

Decompose user input into the following **8 structured components**, each generated independently:

#### 3.1 Subject Description
- Clearly define the subject's appearance, features, and state
- Use specific rather than abstract descriptive terms
- Include: identity/type, appearance features, clothing/material, quantity

#### 3.2 Scene Description
- Environment and background setup
- Include: location, time of day, weather, season, atmosphere keywords

#### 3.3 Camera Language
- Specify shooting angle and camera movement
- Include: shot scale (close-up/medium/wide), angle (high/low/eye-level), movement (dolly/pan/tilt/track/follow)

#### 3.4 Lighting Style
- Define lighting and overall tonal mood
- Include: light source type, light direction, color temperature, tonal style

#### 3.5 Composition Requirements
- Spatial layout of the frame
- Include: composition rules (rule of thirds/symmetry/leading lines), aspect ratio, subject position

#### 3.6 Action & Emotion
- Subject behavior and emotional expression
- Include: action description, expression/emotion, dynamic intensity, rhythm

#### 3.7 Quality Parameters
- Technical quality requirements
- Include: resolution, rendering style, detail level, art style reference

#### 3.8 Negative Prompt
- Elements to be avoided
- Automatically append common negative terms based on generation mode
- Include: quality defects, unwanted elements, style exclusions

### 4. Model-Adapted Output

Apply differentiated adaptation to the structured prompt based on the target model:

**Video Model Adaptation Strategies:**
- **Happy Horse**: **Chinese Prompt mandatory**, camera terms directly usable in Chinese, supports `[Image N]` reference image syntax. Creative Analysis table in Chinese.
- **Seedance**: **Chinese Prompt mandatory**, prioritize subject → action → scene → camera → style in Chinese
- **Kling**: **Chinese Prompt mandatory**, emphasize camera progression, movement methods, and visual texture in Chinese
- **Wanx**: Chinese-English mixed, reduce abstract words, enhance action/scene/camera descriptions
- **Veo**: Complete English description, emphasize visual atmosphere, camera language, temporal rhythm
- **Sora**: Semantically coherent English, clearly define subject relationships, action logic, and scene changes
- **Hailuo**: Concise Chinese, emphasize subject action, emotion, style, and atmosphere
- **Runway**: Natural English + style directives, emphasize visual style consistency and brand tone
- **Pika**: Concise English, emphasize creative effects and transitions (melt/inflate/explode/crumble/Pikascenes), social media optimized, short-form video focus

**Image Model Adaptation Strategies:**
- **Nano Banana**: Concise English, emphasize subject + style + composition + visual effect, photography-grade quality
- **GPT Image**: Natural English, semantically complete and clear, emphasize subject/scene/style/purpose
- **Grok Image**: Natural English description, emphasize visual effects, style, and themes
- **seedream**: **Chinese Prompt mandatory**: subject + scene + lighting + texture + composition in Chinese
- **Qwen Image**: **Chinese Prompt mandatory**, emphasize subject, style, image requirements, and purpose in Chinese
- **Midjourney**: Style + composition + material + lighting keyword combinations, supports `--ar`, `--style`, `::` weight syntax
- **FLUX**: Structured English: subject + scene + style + quality, precise and controllable, API-friendly
- **Ideogram**: Natural English + text content directives, emphasize layout, text readability, and design aesthetics
- **Recraft**: Design-oriented English: subject + style + color palette + output format (raster/vector), supports SVG/EPS vector output, brand style consistency

> For detailed model adaptation rules, see `references/generation-modes.md`
> For prompt templates, see `references/prompt-templates.md`

### 5. Prompt Quality Self-Check (Mandatory Post-Generation)

Perform self-checks on generated prompts before output to ensure quality standards:

#### Self-Check Dimensions

| Check Item | Rule | Action on Failure |
|------------|------|-------------------|
| Intent Completeness | Are all key elements from the user's original description covered? | Add missing elements |
| Component Consistency | Are there semantic conflicts between the 8 components? (e.g., "minimalist style" vs "element-dense") | Resolve conflicts, prioritize user's core intent |
| Length Compliance | Does it meet the target model's prompt length range? Count ONLY the text inside the Positive Prompt code block — exclude markdown markers (```), section headers, labels like "Positive Prompt:", and Negative Prompt content. For English: count space-separated tokens. For Chinese: count characters (excluding punctuation marks and spaces). | If too long, trim by priority; if too short, add details. Report accurate count, not rough estimate. |
| Language Compliance | Does it use the language required by the target model? | Convert to correct language |
| Negative Prompt Validation | Do negative prompts contradict positive descriptions? | Remove contradictory items |
| Physical Plausibility | Are action/scene descriptions physically reasonable? (CRITICAL for video models). Check for: humans hovering/floating in mid-air without mechanical aid, defying gravity, impossible body positions, perpetual motion, objects passing through solid matter, humans remaining perfectly still for extended durations (e.g., 30s frozen), physically impossible camera movements, time-compressed natural processes. | **MUST correct to plausible description AND output ⚠️ Note** in Notes section to inform user of the correction and reasoning |
| Model Feature Adaptation | Does it follow the target model's field order and special syntax? | Rearrange per model specs |

#### Self-Check Process

1. **Quick Scan**: Check length, language, and field order compliance
2. **Physical Plausibility Check (MANDATORY for video models)**: Examine every action and scene description for physical reasonableness. Flag and correct: gravity-defying poses (e.g., person hovering/floating motionless in air), impossible durations (e.g., 30 seconds of perfect stillness), supernatural abilities without context (e.g., a normal human flying), objects violating physics (e.g., passing through walls). When corrected, **⚠️ Note is MANDATORY** — do NOT silently fix; always inform the user.
3. **Semantic Review**: Check inter-component consistency and alignment with user intent
4. **Boundary Check**: Verify no known limitations of the target model are triggered
5. **Final Confirmation**: Confirm the prompt is ready for direct copy-paste use without secondary editing

> Items that fail self-check must be corrected before output. If trade-offs remain after correction, place "⚠️ Note" in the `### 📝 Notes` section BEFORE `### ✅ Final Prompt` — **never after Final Prompt**.
> **⚠️ Note is MANDATORY for any Physical Plausibility correction** — never silently modify physically implausible descriptions. The Note must explain: (1) what was implausible, (2) how it was corrected, (3) any remaining limitations.

---

### 6. Video Parameters Output (Video Models Only)

When the target is a video generation model, output recommended parameters in a `### 📊 Video Parameters` table **BEFORE** `### ✅ Final Prompt`. Never place parameters after Final Prompt.

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| resolution | Resolution | 720P / 1080P / 4K |
| ratio | Aspect Ratio | 16:9 / 9:16 / 1:1 / 4:3 / 3:4 |
| duration | Video Duration | 3-15 seconds (depending on model support) |

---

### 7. Multi-Shot Narrative Mode (Shot Sequence)

When user requirements involve multiple scenes, multiple shots, or storylines, automatically switch to multi-shot sequencing mode:

#### Trigger Conditions
- User description contains multiple scenes/time points ("first...then...finally...")
- User explicitly requests "storyboard", "multi-shot", "shot breakdown"
- Action complexity exceeds single-shot capacity (e.g., cross-scene narrative)

#### Output Structure

```markdown
## 🎬 Multi-Shot Narrative — [Theme]

### Shot Overview
| Shot # | Duration | Scale | Core Content |
|--------|----------|-------|--------|
| Shot 1 | 3s | Wide | [Summary] |
| Shot 2 | 4s | Medium | [Summary] |
| Shot 3 | 3s | Close-up | [Summary] |

### 📝 Narrative Plan

**Transition Suggestions:**
- Shot 1 → Shot 2: [Transition method, e.g., fade/cut/camera-linked]
- Shot 2 → Shot 3: [Transition method]

**Narrative Consistency:**
- Subject Appearance: [Key features to maintain across shots]
- Lighting Continuity: [Ensure adjacent shots have consistent lighting]
- Color Palette: [Unified color scheme]

---

### ✅ Shot Prompts (copy-ready)

**Shot 1 — [Scene Name]:**
```
[Complete Prompt]
```

**Shot 2 — [Scene Name]:**
```
[Complete Prompt]
```

**Shot 3 — [Scene Name]:**
```
[Complete Prompt]
```
```

#### Sequencing Rules
1. Each Shot generates a complete independent Prompt, usable standalone
2. Maintain consistent subject appearance descriptions across shots (use same key feature terms)
3. Adjacent shots must have smooth lighting and color tone transitions
4. Total duration recommended not to exceed 30 seconds (limited by model single-generation capacity)
5. Transition suggestions should consider shot scale changes and emotional rhythm between adjacent shots

---

## Output Format

### Format Design Principles

1. **Analysis First, Delivery Last**: Structured analysis comes first, final copy-ready Prompt at the absolute end
2. **Clear Visual Hierarchy**: Use emoji markers, separators, and code blocks to distinguish areas
3. **End = Deliverable**: `### ✅ Final Prompt` MUST be the last section in output — nothing follows it
4. **At-a-Glance**: Key info (model, mode, language) presented quickly in the top metadata
5. **Notes Before Prompt**: All tips, suggestions, reference explanations, and comparison notes go BEFORE `### ✅ Final Prompt`
6. **Language Consistency**: The Creative Analysis table content and Final Prompt content MUST both be in the target model's designated language. For Chinese-first models, write Creative Analysis table descriptions in Chinese and output Chinese Prompts. For English-first models, write Creative Analysis table descriptions in English and output English Prompts.

### Universal Output Format

```markdown
## 🎬 [Mode Name] | [Target Model]

> 📋 Model: [Model Name] | Language: [Chinese/English] | Suggested Length: [Range]

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | [Specific description] |
| **Scene** | [Specific description] |
| **Camera** | [Specific description] |
| **Lighting** | [Specific description] |
| **Composition** | [Specific description] |
| **Action/Emotion** | [Specific description] |
| **Quality** | [Specific description] |

---

### 📝 Notes (optional, only when needed)

> Model-specific tips, reference image descriptions, or usage notes go here.
> This section MUST appear BEFORE Final Prompt, never after.

---

### 📊 Video Parameters (video models only)

| Parameter | Value |
|-----------|-------|
| Resolution | [720P / 1080P / 4K] |
| Ratio | [16:9 / 9:16 / 1:1] |
| Duration | [3-15s] |

> This section MUST appear BEFORE Final Prompt, never after.

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:
> **NOTHING is allowed after this section — no suggestions, notes, explanations, or any additional text.**

**Positive Prompt:**
```
[Combine all components into a coherent Prompt, ready to paste directly into the model]
```

**Negative Prompt:**
```
[Negative prompt content, only output for models that support negative prompts]
```
```

### HappyHorse Dedicated Output Format

When the target model is HappyHorse, use the following enhanced format:

```markdown
## 🐴 HappyHorse — [Mode Name]

> 📋 Model: `happyhorse-t2v` | Resolution: 1080P | Ratio: 16:9 | Duration: 5s

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | [Specific description] |
| **Scene** | [Specific description] |
| **Camera** | [Specific description] |
| **Lighting** | [Specific description] |
| **Composition** | [Specific description] |
| **Action/Emotion** | [Specific description] |
| **Quality** | [Specific description] |

---

### 📝 Notes (r2v mode: describe reference images here)

**Reference Image Notes (r2v mode only):**
- [Image 1]: [Describe image content and purpose]
- [Image 2]: [Describe image content and purpose]

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:
> **NOTHING is allowed after this section — no suggestions, notes, explanations, or any additional text.**

**Positive Prompt:**
```
[Compose a coherent Chinese Prompt, leveraging HappyHorse's strong understanding of Chinese camera language. This MUST be in Chinese.]
```

**Negative Prompt (use "avoid..." guidance in positive Prompt):**
```
[Negative guidance embedded in positive Prompt using "避免..." phrasing, as HappyHorse does not support independent negative prompts]
```
```

---

## Generation Rules

1. **Language Rules (MANDATORY)**:
   - **Chinese-first models**: Happy Horse, Seedance, Kling, Wanx, Hailuo, seedream, Qwen Image — **MUST output Prompts in Chinese**. The Positive Prompt and Negative Prompt code blocks MUST contain Chinese text. English-only output for these models is a critical error.
   - **English-first models**: Veo, Sora, Runway, Pika, Nano Banana, GPT Image, Grok Image, Midjourney, FLUX, Ideogram, Recraft — **MUST output Prompts in English**. The Positive Prompt and Negative Prompt code blocks MUST contain English text. Chinese-only output for these models is a critical error.
   - **Creative Analysis table content** MUST match the target model's language: Chinese-first models use Chinese descriptions in the Creative Analysis table; English-first models use English descriptions.
   - Explanatory notes (metadata, section headers, labels) always use Chinese
   - When the user explicitly requests a bilingual version, the primary Prompt MUST be in the model's native language, with the alternative language as a secondary version
2. **Precision**: Avoid vague vocabulary (e.g., "nice-looking"), replace with specific descriptions (e.g., "cinematic lighting, golden hour warmth")
3. **Weight Distribution**: Place core elements first, separate with commas, importance decreases from front to back
4. **Length Control**: Generate within the suggested length range for the target model, see model specification tables in `references/generation-modes.md`. Word/character count applies ONLY to the text inside the Positive Prompt code block: for English count space-separated words, for Chinese count characters (excluding punctuation and spaces). Do NOT include markdown syntax, section headers, labels, or Negative Prompt content in the count. Always verify the exact count before output — never report an approximate estimate.
5. **Negative Prompt Handling**: Choose independent negative prompts, positive-guided style, or omit based on model type, see `references/generation-modes.md`
6. **Iterability**: Users can modify any individual component and regenerate
7. **Model-Specific Syntax**:
   - Happy Horse r2v: Use `[Image 1]`, `[Image 2]` in prompts to reference images
   - Midjourney: Supports `--ar 16:9`, `--style raw`, `element::2` weight syntax
   - Stable Diffusion: Supports `(element:1.5)` weight syntax
   - Pika: Supports creative effects keywords (melt, inflate, explode, crumble, Pikascenes), use action verbs for transitions
   - Recraft: Specify output format (raster/vector/icon/illustration), supports brand style references
8. **Over-Length Trimming Priority** (low to high, remove low priority first): Quality Parameters → Composition → Lighting → Scene → Camera → Action/Emotion → Subject (must keep). Maintain semantic coherence when trimming
9. **Prompt Variant Generation**: When users request multiple versions, provide three variants:
   - Conservative: Faithful to user's original description, compact structure, no extra divergence
   - Creative: Diverge from the original, add artistic expressions and unexpected elements
   - Minimal: Shortest effective Prompt, retain only core elements, test model comprehension
10. **Strict Prohibition After Final Prompt**: After `### ✅ Final Prompt` (or `### ✅ Shot Prompts (copy-ready)` in multi-shot mode), **NO additional content is allowed**. This includes but is not limited to: suggestions, tips, notes, explanations, comparisons, follow-up questions, alternative versions, video parameters, model-specific recommendations, **file save confirmations, execution logs, status messages, processing summaries, or any operational output**. The prompt code blocks MUST be the absolute last content in the output. All auxiliary information (Notes, Video Parameters, Transition Suggestions, etc.) must appear BEFORE the Final Prompt section. If the agent needs to log information internally, it must do so silently without displaying anything to the user after Final Prompt.

---

## User Style Configuration (Optional)

If the user expresses preferences during conversation, or demonstrates consistent style tendencies across multiple uses, remember and automatically apply in subsequent generations:

| Configuration | Description | Example |
|---------------|-------------|---------|
| Default Video Model | User's preferred video generation model | Seedance |
| Default Image Model | User's preferred image generation model | Midjourney |
| Preferred Style | User's commonly used visual style | cinematic / Chinese traditional / minimalist / cyberpunk |
| Common Aspect Ratio | User's most common aspect ratio | 16:9 / 9:16 / 1:1 |
| Language Preference | Prompt language preference | Chinese-first / English-first |
| Style Keywords | User's frequently used core style words | cinematic quality, warm tone, shallow DOF |

### Application Rules
- After user first specifies a model, default to that model subsequently (unless explicitly switched)
- When user repeatedly uses specific style words, automatically add to preferred styles
- Style configuration does not override user's explicit instruction for the current session (current instruction has highest priority)
- May proactively ask: "Would you like to set this style as default?"

---

## Model Version Strategy

| Strategy | Description |
|----------|-------------|
| Default Version | Always use the latest stable version of each model |
| User-Specified Version | Support user-specified versions (e.g., "Midjourney", "HappyHorse") |
| Version Feature Differences | When different versions have different prompt rules, generate per specified version rules |
| New Version Release | Update `references/generation-modes.md` to add new version adaptation rules |
| Version Parameters | Midjourney uses `--v` to specify version; other models specify via model name |

---

## Interaction Rules

1. If user input is too brief (fewer than 5 words), ask follow-up questions for more details
2. If generation mode cannot be determined, provide options for user to choose
3. After generation, proactively ask if any component needs adjustment or model switch
4. Support user-specified models, automatically adapt prompt style, language, and length
5. When target is a video model, ask about:
   - Video duration preference
   - Resolution preference
   - Aspect ratio preference
   - Whether reference images are available (determines task type)
6. Support one-click multi-model output: Users can request prompts adapted for multiple models simultaneously
7. Support Prompt variant generation: Users can request "give me different versions", output Conservative/Creative/Minimal variants
8. Remember user preferences: When users repeatedly use a specific model or style, proactively ask whether to set as default

---

## References

| Resource | Path | Description |
|----------|------|-------------|
| Prompt Template Library | `references/prompt-templates.md` | Detailed templates and keyword libraries for each mode |
| Generation Mode Guide | `references/generation-modes.md` | Detailed adaptation rules for each generation mode |
| Usage Examples | `references/examples.md` | Complete input/output examples |
| Acceptance Criteria | `references/acceptance-criteria.md` | Skill quality acceptance criteria |
