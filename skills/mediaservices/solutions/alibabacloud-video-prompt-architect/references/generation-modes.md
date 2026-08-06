# Generation Modes

Detailed adaptation rules and strategy guide for each generation mode.

---

## 1. Text-to-Video

### Applicable Scenarios
- Short video creation, commercials, concept animation, story narration
- User has only text description, no reference images

### Adaptation Strategy
1. **Action Continuity Priority**: Prompt must include clear action descriptions and motion trajectories
2. **Temporal Dimension**: Add temporal flow vocabulary (e.g., "gradually", "seamlessly transitions")
3. **Camera Movement Required**: Specify at least one type of camera movement
4. **Frame Rate Hinting**: Hint at desired frame rate via "smooth motion", "cinematic 24fps", etc.
5. **Duration Awareness**: Hint at reasonable duration based on action complexity

### Component Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Action & Emotion | ★★★★★ | Core driving force |
| Camera Language | ★★★★☆ | Determines visual narrative |
| Subject Description | ★★★★☆ | Ensures subject consistency |
| Scene Description | ★★★☆☆ | Provides environmental context |
| Lighting Style | ★★★☆☆ | Creates atmosphere |
| Quality Parameters | ★★☆☆☆ | Technical assurance |
| Composition | ★★☆☆☆ | Auxiliary reference |

### Special Considerations
- Avoid overly complex scene transition descriptions (single continuous scene works best)
- Match action amplitude with duration (subtle movements suit short segments)
- Multi-subject scenes require clear relative positions and motion relationships

---

## 2. Image-to-Video

### Applicable Scenarios
- Adding dynamic effects to existing static images
- Photo animation, illustration animation
- Localized dynamic effects (e.g., hair flowing, water ripples)

### Adaptation Strategy
1. **Reference Image Consistency**: Prompt must emphasize maintaining original style and color tone
2. **Change Description**: Clearly specify which elements move and which remain static
3. **Motion Amplitude Control**: Use degree words like "subtle", "gentle", "dramatic"
4. **Transition Naturalness**: Emphasize physical plausibility of motion

### Component Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Action & Emotion | ★★★★★ | Defines motion content |
| Subject Description | ★★★★☆ | Aligned with reference image |
| Camera Language | ★★★☆☆ | Camera movement |
| Lighting Style | ★★☆☆☆ | Maintain original lighting |
| Scene Description | ★★☆☆☆ | Already determined by image |
| Quality Parameters | ★★☆☆☆ | Match original quality |
| Composition | ★☆☆☆☆ | Already determined by image |

### Special Considerations
- Always add "maintaining style consistency with reference image"
- Avoid describing elements that contradict the reference image
- Recommend trying motion range from small to large progressively

---

## 3. Text-to-Image

### Applicable Scenarios
- Illustration creation, wallpaper generation, concept design
- Portrait photography, landscape photography simulation
- Artistic creation, stylized imagery

### Adaptation Strategy
1. **Static Composition is King**: Emphasize the perfect frozen-moment quality
2. **Detail Stacking**: Can include more visual detail descriptions
3. **Explicit Style**: Must specify at least one art/photography style
4. **Maximum Quality**: Fully utilize quality-enhancement words

### Component Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Subject Description | ★★★★★ | Core visual focus |
| Lighting Style | ★★★★☆ | Determines overall texture |
| Composition | ★★★★☆ | Key to frame structure |
| Scene Description | ★★★☆☆ | Environmental atmosphere |
| Quality Parameters | ★★★☆☆ | Quality assurance |
| Action & Emotion | ★★☆☆☆ | Frozen moment |
| Camera Language | ★★☆☆☆ | Simulating camera perspective |

### Special Considerations
- Can heavily use comma-separated keyword stacking
- Art style references can cite specific artists or artwork styles
- Note differences in keyword order sensitivity across models

---

## 4. Product Image Generation

### Applicable Scenarios
- E-commerce product hero images, detail images
- Advertising creative materials
- Product concept displays

### Adaptation Strategy
1. **Product as Absolute Subject**: Product must be clear, complete, unobstructed
2. **Commercial-Grade Quality**: Emphasize professional photography quality
3. **Scene Serves the Product**: Background must not overshadow the product
4. **Brand Tone Consistency**: Colors and atmosphere must match brand positioning

### Component Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Subject Description | ★★★★★ | Precise product details |
| Lighting Style | ★★★★★ | Core of commercial photography |
| Composition | ★★★★☆ | Product display angle |
| Quality Parameters | ★★★★☆ | Commercial-grade requirement |
| Scene Description | ★★★☆☆ | Supplementary atmosphere |
| Action & Emotion | ★☆☆☆☆ | Products are mostly static |
| Camera Language | ★☆☆☆☆ | Fixed angles primarily |

### Special Considerations
- Always include "product photography", "commercial quality"
- Background should be clean, avoiding interference with the product
- Pay attention to product proportion and perspective accuracy
- Lighting needs to highlight product material properties

---

## 5. Poster Generation

### Applicable Scenarios
- Marketing posters, event promotions
- Social media graphics, banner ads
- Brand visual materials

### Adaptation Strategy
1. **Layout Awareness**: Must reserve text areas
2. **Visual Hierarchy**: Define foreground, midground, background layers clearly
3. **Color Scheme**: Specify primary and secondary colors
4. **Design Sense**: Use graphic design terminology

### Component Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Composition | ★★★★★ | Layout core |
| Lighting Style | ★★★★☆ | Visual impact |
| Subject Description | ★★★☆☆ | Visual focus |
| Scene Description | ★★★☆☆ | Background design |
| Quality Parameters | ★★★☆☆ | Print-grade requirement |
| Action & Emotion | ★★☆☆☆ | Emotional communication |
| Camera Language | ★☆☆☆☆ | Rarely used |

### Special Considerations
- Must explicitly specify "negative space for text" or "text area"
- Note aspect ratio specification (e.g., 9:16 portrait, 16:9 landscape, 1:1 square)
- Use design terminology for colors rather than vague descriptions
- Consider final output use case (print/screen display)

---

## 6. Video Generation Model Adaptation Layer

### 1. Happy Horse

**Developer**: Alibaba ATH Innovation Division  
**Available Platforms**: Alibaba Cloud Bailian, HappyHorse Official Site, Tongyi Qianwen App  
**Output Specs**: Up to 1080P, 3-15 seconds  
**API Models**: `happyhorse-t2v` / `happyhorse-r2v` / `happyhorse-i2v`

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese; extremely strong understanding of Chinese camera language. English-only output is a critical error. |
| Prompt Length | 100-500 Chinese characters (max 2500); r2v mode 200-800 characters |
| Camera Language | Chinese terms like push, pull, pan, track, follow, high-angle, low-angle directly usable |
| Negative Prompt | No independent parameter; use "avoid..." guidance in positive Prompt |
| Special Syntax | r2v mode uses `[Image 1]`, `[Image 2]` to reference images |
| Field Order | Subject → Camera Movement → Action Details → Atmosphere/Emotion |

**Best Practices:**
- Front-load key details; place subject and action at the beginning
- Use spatial anchor positioning with concrete spatial relationship terms
- Supports multi-shot coherent narrative; Prompt can describe shot transition logic
- Action descriptions must be specific (✅ "she gently raises her hand to unfold the fan" ❌ "she is moving")

**Strength Scenarios**: Character themes, voiceover/lip-sync, camera motion control, short videos, e-commerce showcases  
**Known Limitations (must avoid during generation)**:
- Complex audio-video sync still needs improvement; avoid describing complex sound sync requirements
- Longer videos (>10s) may have physical inconsistencies; recommend ≤5s for complex actions
- Text rendering may be inaccurate; avoid requiring displayed text in Prompts
- Multi-character scenes may cause identity confusion; prefer single subject

---

### 2. Seedance

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese; strong understanding of Chinese descriptions |
| Prompt Length | 80-200 Chinese characters |
| Camera Language | Chinese camera terms directly usable (follow-shot, push-in, pan, high-angle, low-angle, etc.) |
| Negative Prompt | Supports independent negative prompt |
| Field Order | Subject → Action → Scene → Camera → Style |

**Adaptation Focus:**
- Use structured Chinese description, prioritize clearly writing subject, action, scene, camera, and style
- Emphasize action continuity, camera fluidity, and subject consistency
- Suitable for motion shots and dynamic content generation

**Known Limitations (must avoid during generation)**:
- Static scenes perform poorly; ensure Prompt contains clear motion
- Extremely fine hand/fingertip actions may be distorted
- Complex multi-character interactions may produce artifacts

**Applicable Scenarios**: Short videos, narrative segments, motion shots, dynamic content generation

---

### 3. Kling

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese; strong understanding of Chinese camera language and scene descriptions |
| Prompt Length | 80-200 Chinese characters |
| Camera Language | Chinese camera description, emphasizing push-in and movement methods |
| Negative Prompt | Supported |
| Field Order | Subject → Scene → Camera Progression → Visual Texture → Style |

**Adaptation Focus:**
- Use structured Chinese Prompt, enhance video frame details, action performance, camera language, and atmosphere
- Emphasize camera progression, movement methods, and visual texture
- Supports 4K output

**Known Limitations (must avoid during generation)**:
- Very fast actions may produce motion blur
- Multi-scene rapid transitions perform poorly in single generation
- Complex text/logo rendering is unstable

**Applicable Scenarios**: Cinematic videos, advertising videos, drama segments, short film creation

---

### 4. Wanx

| Dimension | Rule |
|-----------|------|
| Language | Chinese-English mixed (strong Chinese semantic understanding; use English for camera/quality terms for better precision) |
| Prompt Length | 50-100 Chinese-English mixed words |
| Camera Language | Chinese terms primarily; key professional terms can use English |
| Negative Prompt | Supported |
| Field Order | Subject → Action → Scene → Camera → Style |

**Adaptation Focus:**
- Emphasize subject stability, natural action, scene coherence
- Use Chinese structured prompt, reduce abstract words, enhance action, scene, and camera descriptions
- Strong Chinese semantic understanding, suitable for native Chinese creation

**Known Limitations (must avoid during generation)**:
- Weak understanding of abstract concepts; avoid overly abstract descriptions
- Excessively long Prompts may cause later content to be ignored; optimal within 100 words
- English camera terms perform better than Chinese translations

**Applicable Scenarios**: Chinese-native video generation, general content creation, marketing videos

---

### 5. Veo

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 100-250 English words |
| Camera Language | Complete English camera description, emphasizing long-take feel |
| Negative Prompt | Positive-guided style, explicitly exclude in Prompt |
| Field Order | Scene Atmosphere → Subject → Camera Language → Temporal Rhythm → Visual Details |

**Adaptation Focus:**
- Favors high-quality, cinematic, long-take feel with high realism
- Descriptions should be more complete, emphasizing visual atmosphere, camera language, temporal rhythm, and scene details
- Suitable for commercials, concept shorts, and other high-quality scenarios

**Known Limitations (must avoid during generation)**:
- Facial details may be distorted in wide shots; recommend medium shot or closer for character scenes
- Slower generation speed, not suitable for rapid iteration
- Complex hand movements may still appear unnatural

**Applicable Scenarios**: High-quality video, commercials, concept shorts, cinematic visuals

---

### 6. Sora

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 100-300 English words |
| Camera Language | Natural language describing camera movement, emphasizing temporal flow |
| Negative Prompt | Positive-guided style |
| Field Order | Subject Relationships → Action Logic → Scene Changes → Camera Movement → Atmosphere |

**Adaptation Focus:**
- Emphasizes complex scene understanding, narrativity, physical consistency, and multi-object interaction
- Descriptions must be clear, complete, semantically coherent; clearly define subject relationships, action logic, and scene changes
- Strong physical world understanding, suitable for complex narratives

**Known Limitations (must avoid during generation)**:
- Extremely short segments (1-2s) not suitable; recommend at least 5s+
- Precise physical interactions (e.g., fluids, collisions) still have defects
- Longer generation time, not suitable for rapid iteration
- Individual features may blur in multi-character scenes

**Applicable Scenarios**: Complex narrative videos, creative shorts, multi-character scenes, concept expression

---

### 7. Hailuo

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese |
| Prompt Length | 30-80 Chinese characters |
| Camera Language | Concise Chinese camera directives |
| Negative Prompt | No independent parameter |
| Field Order | Subject → Action/Emotion → Style/Atmosphere |

**Adaptation Focus:**
- Suitable for lightweight, fast, social-media-oriented video content generation
- Prompt should be concise and direct, emphasizing subject action, emotion, style, and atmosphere
- Avoid excessive keyword stacking

**Known Limitations (must avoid during generation)**:
- Not suitable for complex multi-character narratives; keep scenes simple
- Overly long Prompts will be truncated; strictly control within 80 characters
- Limited precision for complex camera movement control
- No reference image support; text-to-video only

**Applicable Scenarios**: Short videos, social content, light creative expression, quick production

---

### 8. Runway

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 80-200 English words |
| Camera Language | English natural language describing camera movement, supports style directives |
| Negative Prompt | Positive-guided style |
| Field Order | Subject → Action/Scene → Visual Style → Camera Movement → Atmosphere/Texture |

**Adaptation Focus:**
- Emphasizes visual style consistency and brand tone
- Supports multi-model switching (platform integrates Veo)
- Suitable for creative ads, brand videos, stylized content

**Known Limitations (must avoid during generation)**:
- Credits-based system; different resolutions/models consume different credits
- No native 4K support; max 1080p
- Complex physical interactions (e.g., precise fluid simulation) perform poorly
- No official standalone API; platform access only

**Applicable Scenarios**: Creative ads, brand content, stylized videos, marketing shorts

---

### 9. Pika

**Developer**: Pika Labs  
**Available Platforms**: pika.art web app, Discord  
**Output Specs**: Up to 1080p, 3-10 seconds  

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 60-150 English words |
| Camera Language | English natural language, supports creative transition descriptions |
| Negative Prompt | Supported |
| Field Order | Subject → Action → Creative Effect → Scene → Camera → Style |

**Adaptation Focus:**
- Core strength is creative visual effects: melt, inflate, explode, crumble, squish, cake-ify, Pikascenes
- Emphasize action verbs and transition descriptions in prompts
- Social media and short-form video optimized (TikTok, Instagram Reels, YouTube Shorts)
- Prompts should be concise and dynamic, avoid overly long descriptions
- Supports image-to-video with creative transformations

**Known Limitations (must avoid during generation)**:
- Free tier limited to 80 monthly credits at 480p
- Max video length ~10 seconds per generation
- Photorealistic quality below Veo/Sora level
- Complex multi-subject scenes less stable

**Applicable Scenarios**: Social media shorts, creative effects videos, viral content, product demos with visual effects, fun transformations

---

## 7. Image Generation Model Adaptation Layer

### 1. Nano Banana

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 30-80 English words |
| Style | Concise and efficient, photography-grade quality |
| Negative Prompt | Supported |
| Field Order | Subject → Style → Composition → Visual Effect |

**Adaptation Focus**: Suitable for lightweight, fast, creative image generation. Concise and efficient, emphasize subject, style, composition, and visual effects; avoid verbosity.  
**Known Limitations**:
- Not suited for complex scenes and multi-character compositions
- Limited text rendering capability
- Overly long Prompts reduce effectiveness; keep concise

**Applicable Scenarios**: Quick image generation, creative exploration, lightweight visual content

---

### 2. GPT Image

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 50-150 English words |
| Style | Natural language, semantically complete |
| Negative Prompt | Positive-guided style |
| Field Order | Subject → Scene → Style → Purpose |

**Adaptation Focus**: Emphasizes natural language understanding, semantic completeness, and high-quality image expression. Use clear, natural description style.  
**Known Limitations**:
- Weaker control over precise spatial relationships and complex compositions
- No independent negative prompt support; use positive-guided approach
- Specific art style mimicry less precise than Midjourney

**Applicable Scenarios**: General image generation, design sketches, marketing graphics, concept art

---

### 3. Grok Image

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 50-150 English words |
| Style | Natural description, high creative freedom |
| Negative Prompt | Not supported |
| Field Order | Theme → Visual Effect → Style → Emotion |

**Adaptation Focus**: Favors high creative freedom, creative expression, and natural language understanding. Use relatively natural descriptions, emphasizing visual effects, style, and theme expression.  
**Known Limitations**:
- No negative prompt support
- Less precise product photography texture control compared to seedream
- Lower style consistency controllability

**Applicable Scenarios**: Creative images, social media graphics, personalized visual content

---

### 4. seedream

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese; precise understanding of Chinese descriptions |
| Prompt Length | 60-150 Chinese characters |
| Style | Structured Chinese description |
| Negative Prompt | Supports independent negative prompt |
| Field Order | Subject → Scene → Lighting → Texture → Composition |

**Adaptation Focus**: Suitable for high-quality image generation, emphasizing subject details, style, and image completeness. Use Chinese structured description for subject, scene, lighting, texture, and composition.  
**Known Limitations**:
- Strongly stylized rendering (e.g., oil painting, watercolor) less effective than Midjourney
- Spatial relationships in complex scenes may lack precision
- Hand details may still have anomalies

**Applicable Scenarios**: Commercial images, poster graphics, concept art, general high-quality image generation

---

### 5. Qwen Image

| Dimension | Rule |
|-----------|------|
| Language | **MANDATORY Chinese** — Prompt code blocks MUST be in Chinese |
| Prompt Length | 50-150 Chinese characters |
| Style | Chinese-organized requirements |
| Negative Prompt | Supported |
| Field Order | Subject → Style → Image Requirements → Purpose |

**Adaptation Focus**: Strong Chinese comprehension, suitable for Chinese-native prompts. Organize requirements directly in Chinese, emphasizing subject, style, image requirements, and purpose.  
**Known Limitations**:
- English Prompt comprehension less precise than Chinese; stick to Chinese
- Complex photography-grade lighting descriptions may not be fully executed
- Ultra-realistic style detail performance not as strong as specialized models

**Applicable Scenarios**: Chinese design needs, general image generation, marketing visuals, content illustrations

---

### 6. Midjourney

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 40-100 English words |
| Style | Keyword-combination style, emphasizing aesthetics |
| Negative Prompt | Supports `--no` parameter |
| Special Syntax | `--ar 16:9`, `--style raw`, `--v`, `element::2` weight |
| Field Order | Subject → Style Keywords → Material/Lighting → Composition → Parameters |

**Adaptation Focus**: Emphasizes aesthetics, stylization, composition, artistic atmosphere, and visual expression. Suitable for combining style, composition, material, and lighting keywords.  
**Known Limitations**:
- Precise text/logo rendering unreliable
- Hand details may be anomalous (improved in v6+)
- Limited control over precise spatial relationships
- Not suitable for realistic product photos; tends toward artistic style

**Applicable Scenarios**: Posters, concept art, brand visuals, stylized illustrations, high-aesthetic images

---

### 7. FLUX

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 40-120 English words |
| Style | Structured precise description, emphasizing controllability |
| Negative Prompt | Supports independent negative prompt |
| Field Order | Subject → Scene/Background → Style → Lighting/Texture → Quality Parameters |

**Adaptation Focus**: Precise and controllable, suitable for developers and API workflows. Supports multiple model variants (FLUX Pro / Flex / Klein, Kontext); choose based on cost and quality needs.  
**Known Limitations**:
- Consumer product experience less polished than ChatGPT or Midjourney
- Limited text rendering; not suitable for poster/typography use
- Self-hosting requires powerful GPU resources
- Artistic stylization less prominent than Midjourney

**Applicable Scenarios**: API integration, developer workflows, self-hosted deployment, batch image generation, cost-sensitive scenarios

---

### 8. Ideogram

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 30-100 English words |
| Style | Natural language + text content directives |
| Negative Prompt | Supported |
| Field Order | Scene/Layout → Text Content → Subject → Style → Color/Atmosphere |
| Special Capability | Extremely high text rendering accuracy, supports multi-line text layout |

**Adaptation Focus**: Text rendering and layout design are core strengths. Prompt must explicitly specify text content to appear in the image (wrapped in quotes). Supports style reference functionality.  
**Known Limitations**:
- Free outputs are public by default; private generation requires payment
- Realistic portrait precision not as good as GPT Image / Midjourney
- Limited complex scene and multi-subject composition ability
- Oriented toward graphic design; not suitable for pure realistic photography

**Applicable Scenarios**: Poster/ad/cover design, text rendering, typographic images, social media content, marketing materials

---

### 9. Recraft

**Developer**: Recraft AI  
**Available Platforms**: recraft.ai web app, API  
**Output Specs**: Raster (PNG/JPG) and Vector (SVG/EPS) output  

| Dimension | Rule |
|-----------|------|
| Language | English |
| Prompt Length | 30-100 English words |
| Style | Design-oriented, emphasizing output format and brand consistency |
| Negative Prompt | Supported |
| Field Order | Subject → Style/Genre → Color Palette → Composition → Output Format |
| Special Capability | Native SVG/EPS vector output, fully editable and scalable graphics |

**Adaptation Focus**: Design and vector graphics are core strengths. Prompt should specify output format (raster/vector/icon/illustration/mockup) and style category (flat, 3D, line art, pixel art, etc.). Supports brand style references for consistency across assets. Ideal for logos, icons, UI elements, and print materials.  
**Known Limitations**:
- Photorealistic quality below Midjourney / GPT Image
- Less suited for complex multi-subject compositions
- Vector output may require manual cleanup for intricate designs
- Limited photographic/naturalistic style capability

**Applicable Scenarios**: Vector graphics, brand design systems, icons/logos, UI illustrations, print materials, social media graphics, merchandise design
