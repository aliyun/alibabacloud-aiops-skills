# Acceptance Criteria

**Skill**: alibabacloud-video-prompt-architect  
**Purpose**: Skill quality acceptance criteria and test scenarios

---

## Functional Acceptance Criteria

### 1. Intent Recognition Accuracy

#### ✅ CORRECT — Correctly identifies generation mode
| User Input | Expected Mode |
|------------|---------------|
| "A cat running on grass, make it a video" | Text-to-Video |
| "Generate dynamic effects based on this photo" | Image-to-Video |
| "Draw a sunset landscape wallpaper" | Text-to-Image |
| "Product showcase image for our new smartphone" | Product Image Generation |
| "Black Friday promotional poster" | Poster Generation |

#### ❌ INCORRECT — Wrong identification
| User Input | Wrong Judgment | Correct Judgment |
|------------|----------------|------------------|
| "Make a product promotional animation" | Product Image | Text-to-Video |
| "Add some motion to this image" | Text-to-Video | Image-to-Video |

---

### 2. Structured Output Completeness

#### ✅ CORRECT — Output must contain complete structure
```
✓ Title line: Mode name + Target model (format: ## 🎬 [Mode] | [Model])
✓ Metadata line: Model, language, suggested length (format: > 📋 ...)
✓ Creative analysis table: Contains 7 core components (Subject/Scene/Camera/Lighting/Composition/Action-Emotion/Quality)
✓ Notes section (optional): Tips/reference notes, MUST appear BEFORE Final Prompt
✓ Final Prompt area: MUST be the absolute last section, marked with "### ✅ Final Prompt"
✓ Positive prompt: Wrapped in code block, ready for direct copy
✓ Negative prompt: Wrapped in code block (only output for models supporting negative prompts)
✓ NOTHING follows Final Prompt code blocks — no notes, tips, suggestions, or comparisons after it
```

#### ✔️ Format Hierarchy Standards
```
✓ Analysis first, delivery last: Creative analysis first, final Prompt at the absolute end
✓ Notes/tips/suggestions MUST be placed BEFORE "### ✅ Final Prompt", never after
✓ User can copy directly at the end without scrolling back
✓ Use separators (---) to distinguish analysis area from delivery area
✓ All copyable content wrapped in code blocks (```)
```

#### ✖ INCORRECT — Format errors
```
✗ Missing Metadata line (model/language/length info)
✗ Final Prompt not at the end, placed in the middle of analysis
✗ Notes/suggestions/tips/comparisons appear AFTER Final Prompt code blocks
✗ ANY text appears after Final Prompt (e.g., follow-up questions, alternative suggestions, "would you like...", model recommendations, video parameters, usage tips, file save confirmations, execution logs, processing status messages)
✗ Video parameters table placed AFTER Final Prompt instead of before
✗ Copyable Prompt not wrapped in code block
✗ Component content is empty or contains only placeholders
✗ Uses vague vocabulary (e.g., "nice lighting" instead of specific lighting description)
```

---

### 3. Prompt Language and Quality

#### ✅ CORRECT
- English-first models (Veo/Sora/Runway/Nano Banana/GPT Image/Grok Image/Midjourney/FLUX/Ideogram) → Prompt output **MUST be in English**
- Chinese-first models (Happy Horse/Seedance/Kling/Wanx/Hailuo/seedream/Qwen Image) → Prompt output **MUST be in Chinese** (positive and negative prompt code blocks contain Chinese text)
- Creative Analysis table content matches the target model's designated language
- Explanatory notes always in Chinese
- No vague vocabulary; all specific descriptive terms
- Keywords ordered by importance
- Length within target model's required range
- Word/character count reported in self-check accurately matches the actual content of the Positive Prompt code block

#### ❌ INCORRECT
- English-first model outputs Chinese Prompt
- Chinese-first model (e.g., Happy Horse) outputs English Prompt — **this is a critical error**
- Chinese-first model's Positive Prompt code block contains only English text
- Creative Analysis table uses English for a Chinese-first model, or Chinese for an English-first model
- Contains meaningless generic words like "beautiful", "nice", "good"
- Prompt length outside target model's allowed range
- Reported word/character count significantly deviates from the actual count (e.g., claims ~170 words but actual count is ~135)
- Keywords in no logical order

---

### 4. Negative Prompt Quality

#### ✅ CORRECT
- Contains basic quality exclusion words (low quality, blurry, distorted, etc.)
- Contains mode-specific exclusion words (e.g., flickering, jittering for video mode)
- Contains scene-relevant exclusion words

#### ❌ INCORRECT
- Negative prompt is empty
- Contains only generic exclusion words with no scene targeting
- Negative prompt contradicts positive prompt

---

### 5. Mode Adaptation Correctness

#### ✅ CORRECT — Text-to-Video mode
- Contains action continuity description
- Contains at least one type of camera movement
- Contains temporal flow vocabulary
- Prompt length meets target model requirements

#### ✅ CORRECT — Image-to-Video mode
- Contains style consistency description
- Clearly specifies motion elements and static elements
- Motion description is physically plausible

#### ✅ CORRECT — Text-to-Image mode
- Emphasizes static composition and detail
- Contains explicit art/photography style
- Uses quality enhancement words
- Prompt length meets target model requirements

#### ✅ CORRECT — Product Image mode
- Product is the absolute focus
- Contains "product photography" related terminology
- Background is clean and non-interfering
- Prompt length meets target model requirements

#### ✅ CORRECT — Poster mode
- Contains text area reservation description
- Specifies aspect ratio
- Uses design terminology
- Prompt length meets target model requirements

---

### 6. Interaction Experience

#### ✅ CORRECT
- Proactively asks follow-up when input is too brief
- Provides options when mode cannot be determined
- Asks if adjustments are needed after generation
- Supports modifying a single component and regenerating

#### ❌ INCORRECT
- Generates directly for any input without confirmation
- Regenerates everything when user requests modification to one component
- Does not provide selectable generation modes

---

---

### 7. Model Adaptation Acceptance

#### Video Model Adaptation Acceptance

| Model | Language Requirement | Length Range | Must Check |
|-------|---------------------|-------------|------------|
| Happy Horse | Chinese-first | 100-500 characters | No independent negative prompt; field order: Subject→Camera→Action→Atmosphere |
| Seedance | Chinese-first | 80-200 characters | Supports independent negative prompt; field order: Subject→Action→Scene→Camera→Style |
| Kling | Chinese-first | 80-200 characters | Supports independent negative prompt; field order: Subject→Scene→Camera Progression→Visual Texture→Style |
| Wanx | Chinese-English mixed | 50-100 words | Supports negative prompt; field order: Subject→Action→Scene→Camera→Style |
| Veo | English | 100-250 words | Positive-guided negative prompt; field order: Scene Atmosphere→Subject→Camera→Temporal Rhythm→Details |
| Sora | English | 100-300 words | Positive-guided; field order: Subject Relationships→Action Logic→Scene Changes→Camera→Atmosphere |
| Hailuo | Chinese | 30-80 characters | No independent negative prompt; field order: Subject→Action/Emotion→Style/Atmosphere |
| Runway | English | 80-200 words | Positive-guided; field order: Subject→Action/Scene→Visual Style→Camera Movement→Atmosphere |
| Pika | English | 60-150 words | Supports negative prompt; field order: Subject→Action→Creative Effect→Scene→Camera→Style |

#### Image Model Adaptation Acceptance

| Model | Language Requirement | Length Range | Must Check |
|-------|---------------------|-------------|------------|
| Nano Banana | English | 30-80 words | Supports negative prompt; concise and efficient, emphasize subject+style+composition |
| GPT Image | English | 50-150 words | Positive-guided; natural language description |
| Grok Image | English | 50-150 words | No negative prompt; natural description style |
| seedream | Chinese-first | 60-150 characters | Supports independent negative prompt; structured Chinese description |
| Qwen Image | Chinese | 50-150 characters | Supports negative prompt; Chinese-organized requirements |
| Midjourney | English | 40-100 words | Supports `--no`; must include parameters (--ar/--style/--v); supports `::` weight |
| FLUX | English | 40-120 words | Supports independent negative prompt; structured precise description; field order: Subject→Scene→Style→Lighting→Quality |
| Ideogram | English | 30-100 words | Supports negative prompt; text content must be wrapped in quotes; field order: Layout→Text→Subject→Style→Color |
| Recraft | English | 30-100 words | Supports negative prompt; specify output format (vector/raster/icon/illustration); field order: Subject→Style/Genre→Color Palette→Composition→Output Format |

#### Model-Specific Syntax Acceptance

| Scenario | Expected Output |
|----------|-----------------|
| User specifies HappyHorse r2v | Prompt contains `[Image N]` syntax |
| User specifies Midjourney | Prompt ends with `--ar`, `--style` and other parameters |
| User specifies Midjourney and emphasizes an element | Uses `element::2` weight syntax |
| User specifies Hailuo | Prompt is concise Chinese, not exceeding 80 characters |
| User specifies Runway | Prompt is English, contains visual style directives and camera movement description |
| User specifies FLUX | Prompt is structured English, includes independent negative prompt |
| User specifies Ideogram | Prompt contains quote-wrapped text content directives |
| User specifies Pika | Prompt is concise English, contains creative effect keywords (melt/inflate/explode/crumble/Pikascenes) |
| User specifies Recraft | Prompt specifies output format (vector/raster/icon/illustration), contains style/genre and color palette |
| User requests "generate for multiple models simultaneously" | Outputs multiple prompts adapted for different models |

---

### 8. Multi-Shot Narrative Acceptance

#### ✅ CORRECT
- Multi-scene descriptions automatically trigger multi-shot mode
- Each Shot contains a complete independent Prompt
- Subject description is consistent across shots
- Includes transition suggestions
- Includes narrative consistency requirements

#### ❌ INCORRECT
- Multi-scene requirements still use single-shot format output
- Subject description inconsistent across shots (e.g., black hair in Shot 1, changes to blonde in Shot 2)
- Missing transition suggestions
- Sudden lighting/color tone changes between Shots without explanation

---

### 9. Prompt Quality Self-Check Acceptance

#### ✅ CORRECT
- Pre-output self-check passed for intent completeness, component consistency, length compliance, language compliance, etc.
- Physical Plausibility check performed: gravity-defying actions, impossible durations, supernatural feats detected and corrected
- When physical plausibility is corrected, ⚠️ Note is output explaining what was implausible and how it was corrected
- Trade-offs marked with "⚠️ Note" to inform user
- Negative prompt does not contradict positive description

#### ❌ INCORRECT
- Output Prompt contains unresolved semantic conflicts between components
- Length exceeds model limit without trimming
- Negative prompt contradicts positive description
- Physically implausible descriptions (e.g., human hovering motionless for 30 seconds, defying gravity) pass through without correction
- Physical plausibility correction applied silently without ⚠️ Note to inform user
- ⚠️ Note missing when physical implausibility was detected and corrected

---

## Boundary Test Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| User inputs only 2 words "landscape" | Ask follow-up questions for more details |
| User mentions both "video" and "poster" simultaneously | Ask to confirm priority mode |
| User specifies a model "use Midjourney" | Adapt to MJ syntax format, include --ar/--style/--v parameters |
| User specifies "use Hailuo to generate video" | Output concise Chinese Prompt, not exceeding 80 characters |
| User requests Chinese Prompt + English model | Explain English works best, also provide Chinese reference version |
| User provides reference image without text description | Identify as Image-to-Video, ask about desired dynamic effects |
| User describes multi-scene narrative | Automatically trigger multi-shot mode |
| User requests "give me both Seedance and Kling versions" | Output two separately adapted Prompts |
| User requests "give me 3 different styles" | Output Conservative/Creative/Minimal three variants |
| User describes physically implausible action "a person hovers motionless in mid-air for 30 seconds" | Detect physical implausibility, correct to plausible description (e.g., slow-motion jump, wire-fu effect, zero-gravity simulation), output ⚠️ Note explaining the correction. NEVER generate the physically impossible description as-is without correction or warning. |
| User describes supernatural feat without context "a normal person flies across the sky" | Detect as physically implausible, offer plausible alternatives (e.g., wire-fu, dream sequence, superhero context with explicit genre framing), output ⚠️ Note |
| Agent generates Veo prompt and self-reports "approximately 170 words" | Actual word count of Positive Prompt code block must be within ±10% of reported number. Count only space-separated tokens inside the code block, exclude markdown/headers/labels. |
| Agent finishes output after Final Prompt code blocks | Absolutely NO text follows the closing ``` of the last prompt code block — no file save confirmations, no execution logs, no status messages, no "done" indicators. |
