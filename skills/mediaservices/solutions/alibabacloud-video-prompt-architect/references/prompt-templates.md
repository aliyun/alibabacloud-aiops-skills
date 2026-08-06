# Prompt Templates Library

Detailed templates and keyword libraries for each generation mode, referenced during Skill execution.

---

## Universal Structure Template

```
[Subject] + [Scene] + [Camera] + [Lighting] + [Composition] + [Action/Emotion] + [Quality] 
```

---

## 1. Text-to-Video Templates

### HappyHorse Chinese Template (Recommended)

```
[主体外观描述]，[场景环境]，[镜头运动与角度变化]，[光影氛围]，[动作与情绪细节]，[电影级质感描述]
```

**Typical Example:**
```
一位身着浅粉色飘逸长裙的少女，黑色长发随风飘动，在盛开的樱花树下翩翩起舞。
镜头以中景侧面起始，缓慢环绕拉远至全景，低角度仰拍。
柔和的自然光透过花瓣洒落，黄金时刻暖调，斑驳光影在她身上跳动。
她优雅旋转，双臂展开，裙摆随动作飞扬，花瓣在她身边旋转飘落，
神情喜悦而自由，电影级叙事质感。
```

### Model-Specific Templates

### Seedance Template
> Field order: Subject → Action → Scene → Camera → Style

```
[主体外观特征] [动作连续性描述]，[场景环境]，
[镜头运动]，[光影与氛围]，[视觉风格]，
动作流畅，主体一致，电影级质感
```

### Kling Template
> Field order: Subject → Scene → Camera Progression → Visual Texture → Style

```
[主体描述]，[场景与氛围]，
[镜头推拉/跟移描述]，[画面质感与质量]，
[电影风格]，细节丰富，高清画质，电影级质感
```

### Veo Template
> Field order: Scene Atmosphere → Subject → Camera Language → Temporal Rhythm → Visual Details

```
[Atmospheric scene description], [subject within environment],
[long take camera movement], [temporal rhythm and pacing],
[fine detail description], cinematic, high-fidelity, photorealistic
```

### Sora Template
> Field order: Subject Relationships → Action Logic → Scene Changes → Camera Movement → Atmosphere

```
[Clear subject relationships and spatial arrangement]. 
[Action logic and sequence]. [Scene evolution over time]. 
[Camera movement description]. [Mood and atmosphere]. 
Physically consistent, narrative coherent.
```

### Hailuo Template
> Field order: Subject → Action/Emotion → Style/Atmosphere

```
[主体]，[动作/情绪]，[风格/氛围]
```

### Wanx Template
> Field order: Subject → Action → Scene → Camera → Style

```
[主体描述]，[动作]，[场景]，[camera movement]，[cinematic quality]
```

### Keyword Library

**Camera Movement Vocabulary:**
- dolly in, dolly out, tracking shot, crane shot, pan left/right
- slow motion, timelapse, hyperlapse, orbit shot, push in
- steady cam, handheld, aerial shot, zoom in/out, whip pan

**Temporal Flow Vocabulary:**
- seamless transition, continuous shot, flowing movement
- gradual change, morphing, evolving scene

**Dynamic Emphasis Vocabulary:**
- dynamic movement, fluid motion, energetic pace
- smooth animation, natural motion blur, cinematic flow

### Typical Template Example
```
A [subject with details] is [action with emotion], in [scene with atmosphere], 
[camera movement] shot, [lighting style], [color grading], 
cinematic quality, 4K resolution, smooth motion, 24fps film look
```

---

## 2. Reference-to-Video Template — HappyHorse Exclusive

### Template Structure
```
[Image N]中[具体对象描述]，[镜头运动序列]，[多角色互动描述]，[细节捕捉]，[氛围和情感]
```

### Key Rules
- Use `[Image 1]`, `[Image 2]` to reference corresponding images in the media array
- Must clearly describe specific objects in reference images (e.g., "woman in a red qipao")
- Supports 1-9 reference images
- Image requirements: short edge ≥400px, recommended 720P+, single image ≤10MB

### Typical Example
```
[Image 1]中身着红色旗袍的女性，镜头先以侧面中景勾勒旗袍修身剪裁与S型曲线，
随即切换至低角度仰拍，捕捉她轻抬玉手展开[Image 2]中的折扇的同时，
[Image 3]中的流苏耳坠随头部转动轻盈摆动的细节，
最后推近至面部特写，定格在她指尖轻点扇骨、眼波流转间的含蓄风情，
多视角全方位展现东方韵味。
```

---

## 3. Image-to-Video Templates

### Template Structure
```
[基于参考图的变化描述], [运动方向], [过渡效果], [氛围延续], [画质保持]
```

### Keyword Library

**Motion Description:**
- gentle sway, subtle movement, breathing effect
- parallax motion, depth shift, slow reveal
- hair flowing, cloth waving, water rippling

**Transition Effects:**
- smooth transition, seamless loop, gradual reveal
- zoom through, morph into, dissolve to

### Typical Template Example
```
Starting from the reference image, [describe motion/change], 
[camera movement], maintaining [style consistency], 
[duration/speed indication], seamless and natural motion
```

---

## 4. Text-to-Image Templates

### Model-Specific Templates

**Nano Banana (concise and efficient, photography-grade quality):**
> Field order: Subject → Style → Composition → Visual Effect

```
[Subject], [style], [composition], [visual effect], [quality keywords]
```

**GPT Image (natural language):**
> Field order: Subject → Scene → Style → Purpose

```
A [detailed subject description] in [scene], with [lighting and mood], 
[style and purpose], [quality description]
```

**Grok Image (free creativity):**
> Field order: Theme → Visual Effect → Style → Emotion

```
[Theme/concept], [visual effect], [style and mood], [emotional tone]
```

**seedream (structured high-quality):**
> Field order: Subject → Scene → Lighting → Texture → Composition

```
[主体细节]，[场景/背景]，[光影与质感]，
[构图方式]，[画质]，[艺术风格]
```

**Qwen Image (Chinese-native):**
> Field order: Subject → Style → Image Requirements → Purpose

```
[主体描述]，[风格]，[画面要求]，[用途场景]
```

**Midjourney (keyword combination + parameters):**
> Field order: Subject → Style Keywords → Material/Lighting → Composition → Parameters

```
[Subject], [style keywords], [material/texture], [lighting], [composition] --ar 16:9 --style raw
```

### Universal Structure
```
[主体细节], [场景描写], [构图方式], [光影风格], [艺术风格], [画质参数]
```

### Keyword Library

**Art Styles:**
- photorealistic, hyperrealistic, cinematic still
- oil painting style, watercolor, digital art, anime style
- concept art, illustration, 3D render, miniature

**Quality Enhancement Words:**
- masterpiece, best quality, ultra-detailed, sharp focus
- 8K UHD, high resolution, professional photography
- RAW photo, DSLR quality, studio lighting

**Composition Vocabulary:**
- rule of thirds, centered composition, golden ratio
- leading lines, symmetrical, dynamic angle
- close-up portrait, full body shot, wide angle landscape

### Typical Template Example
```
[Subject with precise details], [scene/background], 
[composition style], [lighting description], 
[art style], masterpiece, best quality, ultra-detailed, 8K
```

---

## 5. Product Image Templates

### Template Structure
```
[产品描述], [展示角度], [场景氛围], [品牌调性], [商业级画质]
```

### Keyword Library

**Display Methods:**
- product photography, studio shot, floating product
- lifestyle shot, flat lay, 45-degree angle
- hero shot, detail close-up, exploded view

**Scene Vocabulary:**
- minimalist background, gradient backdrop, natural setting
- luxury surface, marble table, wooden display
- contextual use, in-hand shot, scale reference

**Brand Tone:**
- premium feel, luxury brand aesthetic, clean and modern
- tech-forward, organic and natural, playful and vibrant

### Typical Template Example
```
Professional product photography of [product details], 
[angle/perspective], [background/surface], [lighting setup], 
commercial quality, crisp details, [brand mood], 8K product shot
```

---

## 6. Poster Generation Templates

### Template Structure
```
[视觉主体], [排版留白], [色彩方案], [设计风格], [文字区域指示]
```

### Keyword Library

**Design Styles:**
- minimalist poster design, bold typography space
- gradient background, geometric layout, editorial design
- retro poster, modern clean, brutalist design

**Layout Directives:**
- large text area at top/bottom, negative space for copy
- balanced layout, visual hierarchy, focal point
- bleed edge design, centered alignment, asymmetric balance

**Color Description:**
- monochromatic palette, complementary colors
- warm tones, cool blues, vibrant contrast
- pastel soft, neon glow, earth tones

### Typical Template Example
```
[Design style] poster layout, [main visual element], 
[color scheme], [composition with text areas], 
clean design, print quality, [aspect ratio], 
generous negative space for typography
```

---

## 6-B. Runway Video Template

### Template Structure
```
[Subject description] [action/movement], [scene and environment],
[visual style and brand tone], [camera movement],
[lighting and mood], cinematic quality, style-consistent
```

### Keyword Library

**Visual Styles:**
- brand-aligned aesthetic, consistent color grading, editorial look
- vintage film tone, modern minimalist, high-fashion editorial
- neon-lit cyberpunk, warm lifestyle, cold corporate clean

**Camera Movement:**
- smooth dolly forward, orbital pan, slow reveal
- handheld follow, steady tracking shot, crane ascending
- static lock-off, whip pan transition, slow zoom out

### Typical Template Example
```
[Subject] performing [action] in [environment],
[brand visual style], [camera movement],
[lighting atmosphere], cinematic grade,
style-consistent, professional production quality
```

---

## 6-B2. Pika Video Template

### Template Structure
```
[Subject description] [action/movement], [creative effect keyword],
[scene and environment], [camera movement],
[style and mood], [transition description]
```

### Keyword Library

**Creative Effects:**
- melt into, inflate and expand, explode into fragments, crumble to dust
- squish and compress, cake-ify, turn into liquid, dissolve away
- Pikascenes: transition between scenes with seamless morphing

**Action Verbs:**
- transform into, morph into, burst into, collapse into
- flow like, ripple through, shatter into, reform as

**Camera & Transitions:**
- quick zoom in, snap cut, smooth morph transition
- whip pan, dynamic tilt, orbital spin
- seamless scene transition, match cut

### Typical Template Example
```
[Subject] [action], then [creative effect keyword],
[scene description], [camera movement],
[style/mood], dynamic transition, social media ready
```

---

## 6-C. FLUX Image Template

### Template Structure
```
[Subject with precise details], [scene/background], [style],
[lighting and texture], [quality parameters]
```

### Keyword Library

**Quality Control:**
- highly detailed, sharp focus, professional quality
- 8K resolution, ultra-realistic, photorealistic rendering
- masterpiece, best quality, absurdres

**Style Control:**
- digital art, oil painting, watercolor, photograph
- concept art, anime style, 3D render, vector illustration
- cinematic still, editorial photography, fashion shoot

### Typical Template Example
```
[Detailed subject description], [scene/environment],
[art style], [lighting], [quality: highly detailed, sharp focus, 8K]
```

**Negative Prompt Template:**
```
low quality, blurry, artifacts, distorted, deformed,
bad anatomy, watermark, text, signature
```

---

## 6-D. Ideogram Image Template

### Template Structure
```
[Design type/layout], text "[exact text to render]",
[visual subject], [style and color scheme], [mood/atmosphere]
```

### Keyword Library

**Text Directives:**
- text "Your Text Here" in bold sans-serif font
- headline reading "Title" at the top
- elegant script typography saying "Brand Name"

**Layout Styles:**
- poster layout, magazine cover, social media card
- billboard design, book cover, event flyer
- infographic style, logo design, typography art

**Design Elements:**
- clean negative space, balanced composition, visual hierarchy
- gradient background, geometric patterns, organic shapes
- vibrant contrast, monochrome elegance, pastel harmony

### Typical Template Example
```
[Design type] featuring text "[exact text]",
[visual subject/background], [color scheme],
[design style], clean layout, professional quality,
readable typography, balanced composition
```

---

## 6-E. Recraft Image Template

### Template Structure
```
[Subject with precise details], [style/genre],
[color palette], [composition/layout],
[output format: vector/raster/icon/illustration]
```

### Keyword Library

**Output Formats:**
- vector graphic, SVG output, scalable vector, flat icon
- raster illustration, pixel art, 3D render, line art
- logo design, brand mark, UI illustration, mockup

**Style Categories:**
- flat design, minimal geometric, isometric, hand-drawn sketch
- corporate memphis, duotone, gradient mesh, retro pixel
- watercolor texture, engraving style, stencil art, badge design

**Color Palettes:**
- brand colors: [primary, secondary, accent]
- monochrome, duotone, muted earth tones, vibrant neon
- pastel harmony, corporate blue palette, warm sunset gradient

### Typical Template Example
```
[Subject description], [style/genre] style,
[color palette], clean [composition],
[output format], professional design quality,
scalable, brand-consistent
```

---

## 7. Universal Negative Prompt Library

### Basic Quality Exclusions (all modes)
```
low quality, blurry, pixelated, noisy, artifacts, 
distorted, deformed, ugly, disfigured, 
watermark, text overlay, signature, logo,
oversaturated, underexposed, overexposed
```

### Character-Related Exclusions
```
extra limbs, extra fingers, mutated hands, bad anatomy,
bad proportions, cloned face, duplicate, 
cross-eyed, asymmetric eyes, unnatural pose
```

### Video-Specific Exclusions
```
flickering, jittering, frame drops, inconsistent lighting,
morphing artifacts, temporal inconsistency, 
sudden cuts, unnatural motion, static frame
```

### Product Image-Specific Exclusions
```
unrealistic proportions, incorrect perspective,
branding errors, color cast, unwanted reflections,
cluttered background, distracting elements
```

### Poster-Specific Exclusions
```
busy composition, illegible text area, unbalanced layout,
clashing colors, poor contrast, amateur design,
overcrowded elements, no breathing room
```
