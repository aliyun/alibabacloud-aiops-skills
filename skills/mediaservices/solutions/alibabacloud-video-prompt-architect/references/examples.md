# Usage Examples

Complete input/output examples demonstrating the Skill's actual working results.

---

## Example 1: HappyHorse Text-to-Video (Chinese Prompt)

### User Input
> "我想生成一个视频，一个女孩在樱花树下跳舞，用 HappyHorse"

### Output

## 🐴 HappyHorse — Text-to-Video

> 📋 Model: `happyhorse-t2v` | Resolution: 1080P | Ratio: 16:9 | Duration: 5s

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | "一位身着浅粉色飘逸长裙的少女，黑色长发如瀑布般垂落" |
| **Scene** | "盛开的樱花树下，粉色花瓣在春风中轻柔飘落，背景是宁静的日式庭院" |
| **Camera** | "以中景侧面起始，缓慢环绕主体拉远至全景，低角度仰拍" |
| **Lighting** | "柔和自然光透过樱花树枝洒落，黄金时刻暖调，斑驳光影" |
| **Composition** | "主体居中，樱花枝条从上方自然垂落构成画框" |
| **Action/Emotion** | "优雅旋转起舞，双臂展开，裙摆随动作飞扬，花瓣在身边旋转，神情喜悦而自由" |
| **Quality** | "电影级叙事质感，4K画质，浅景深，自然运动模糊" |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
一位身着浅粉色飘逸长裙的少女，黑色长发如瀑布般垂落，在盛开的樱花树下翩翩起舞。镜头以中景侧面起始，缓慢环绕主体拉远至全景，低角度仰拍。柔和的自然光透过樱花树枝洒落，黄金时刻暖调，斑驳光影在她身上跳动。她优雅旋转，双臂展开，裙摆随动作飞扬，粉色花瓣在她身边旋转飘落，神情喜悦而自由，电影级叙事质感。
```

**Negative Prompt (embedded guidance):**
```
避免模糊画面，避免低质量，避免变形，避免多余肢体
```

---

## Example 2: HappyHorse Reference-to-Video (Multi-Image Fusion)

### User Input
> "我有一张旗袍女性的照片、一张折扇的图片和一张流苏耳坠的图，想生成一个展现东方韵味的视频"

### Output

## 🐴 HappyHorse — Reference-to-Video

> 📋 Model: `happyhorse-r2v` | Resolution: 1080P | Ratio: 16:9 | Duration: 5s

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | "[Image 1] 中身着红色旗袍的女性，体态优雅" |
| **Scene** | "精致的东方美学场景，柔光映衬" |
| **Camera** | "侧面中景 → 低角度仰拍 → 面部特写，多视角切换" |
| **Lighting** | "柔和侧光，温暖金色调，突出旗袍面料质感" |
| **Composition** | "主体三分构图，留白东方美学，折扇形成对角线引导" |
| **Action/Emotion** | "轻抬玉手展开折扇，流苏耳坠随头部转动摆动，含蓄风情" |
| **Quality** | "东方美学电影质感，细腻肤质，高还原度色彩" |

---

### 📝 Notes

**Reference Image Notes:**
- **[Image 1]**: Woman in red qipao — video main character
- **[Image 2]**: Folding fan — interactive prop
- **[Image 3]**: Tassel earrings — detail accessory element

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
[Image 1]中身着红色旗袍的女性，镜头先以侧面中景勾勒旗袍修身剪裁与S型曲线，随即切换至低角度仰拍，捕捉她轻抬玉手展开[Image 2]中的折扇的同时，[Image 3]中的流苏耳坠随头部转动轻盈摆动的细节，最后推近至面部特写，定格在她指尖轻点扇骨、眼波流转间的含蓄风情，多视角全方位展现东方韵味。
```

---

## Example 3: Text-to-Video (Universal English Mode)

### User Input
> "一个女孩在樱花树下跳舞，用 Veo"

### Output

## 🎬 Text-to-Video | Veo

> 📋 Model: Veo | Language: English | Suggested Length: 100-250 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | A young Asian woman with long flowing black hair, wearing a light pink flowing dress with delicate floral patterns |
| **Scene** | Under a blooming cherry blossom tree, soft pink petals falling gently in the spring breeze, a serene Japanese garden in the background |
| **Camera** | Medium shot slowly pulling back to wide shot, gentle orbit movement around the subject, low angle |
| **Lighting** | Soft natural daylight filtered through cherry blossoms, warm golden hour tones, dappled light creating beautiful shadows |
| **Composition** | Subject centered with cherry blossom branches framing the top, rule of thirds for depth |
| **Action/Emotion** | Graceful ballet-inspired dance, spinning with arms extended, joyful and free expression, dress flowing with movement, petals swirling around her |
| **Quality** | Cinematic quality, 4K resolution, shallow depth of field, film grain, 24fps smooth motion |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
A young Asian woman with long flowing black hair, wearing a light pink flowing dress with delicate floral patterns, gracefully dancing and spinning with arms extended under a blooming cherry blossom tree, soft pink petals falling gently around her, serene Japanese garden background, medium shot slowly orbiting to wide shot, low angle, soft natural daylight filtered through blossoms, warm golden hour tones, dappled light, joyful and free expression, dress flowing with movement, cinematic quality, 4K, shallow depth of field, smooth motion, 24fps film look
```

**Negative Prompt:**
```
low quality, blurry, pixelated, distorted face, extra limbs, bad anatomy, flickering, jittering, inconsistent lighting, static frame, watermark, text overlay, unnatural motion, morphing artifacts
```

---

## Example 4: Product Image Generation

### User Input
> "一款白色无线蓝牙耳机的产品展示图"

### Output

## 🎬 Product Image | GPT Image

> 📋 Model: GPT Image | Language: English | Suggested Length: 50-150 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | Sleek white wireless Bluetooth earbuds with charging case, minimalist design, matte finish with subtle glossy accents |
| **Scene** | Clean minimalist white-grey gradient background, soft reflective surface beneath the product |
| **Camera** | 45-degree angle hero shot, slight elevation to show both earbuds and open case |
| **Lighting** | Professional studio lighting, soft key light from upper left, gentle fill light, subtle rim light highlighting product edges, clean shadows |
| **Composition** | Product centered, generous negative space, clean and balanced, slight off-center for dynamic feel |
| **Action/Emotion** | Static product display, premium and sophisticated mood |
| **Quality** | Commercial product photography, 8K ultra-sharp, crisp details, color-accurate, professional retouching |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Professional product photography of sleek white wireless Bluetooth earbuds with open charging case, minimalist matte finish with glossy accents, 45-degree hero shot angle, clean white-grey gradient background, soft reflective surface, professional studio lighting with soft key light from upper left and rim light highlighting edges, centered composition with generous negative space, premium sophisticated mood, commercial quality, 8K ultra-sharp, crisp details, color-accurate
```

**Negative Prompt:**
```
low quality, blurry, incorrect proportions, unrealistic perspective, color cast, unwanted reflections, cluttered background, distracting elements, watermark, text, amateur lighting, harsh shadows
```

---

## Example 5: Poster Generation

### User Input
> "夏日音乐节宣传海报，要活力四射的感觉"

### Output

## 🎬 Poster Generation | Midjourney

> 📋 Model: Midjourney | Language: English | Suggested Length: 40-100 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | Abstract musical elements — guitar silhouette, sound waves, musical notes transforming into colorful energy bursts |
| **Scene** | Vibrant summer sunset backdrop with tropical palm tree silhouettes, warm sky gradients from orange to purple |
| **Camera** | Flat graphic perspective, poster-oriented front view |
| **Lighting** | Bold neon color splashes over warm sunset gradient, high contrast, vibrant saturated colors with electric blue and hot pink accents |
| **Composition** | Large text area reserved at top third for event title, visual elements concentrated in lower two-thirds, asymmetric dynamic balance, 2:3 portrait |
| **Action/Emotion** | Energetic, celebratory, summer freedom, youthful excitement |
| **Quality** | Print-ready quality, vector-clean edges, bold graphic design style, vivid colors |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Vibrant summer music festival poster design, abstract musical elements with guitar silhouette and colorful energy bursts, tropical sunset backdrop with palm tree silhouettes, warm orange to purple gradient sky, bold neon color splashes with electric blue and hot pink accents, high contrast vivid saturated colors, large negative space at top for title text, visual elements in lower two-thirds, asymmetric dynamic composition, 2:3 portrait ratio, energetic celebratory mood, print-ready quality, bold graphic design style, editorial poster aesthetic
```

**Negative Prompt:**
```
busy composition, illegible text area, unbalanced layout, dull colors, poor contrast, amateur design, overcrowded elements, no breathing room, photorealistic style, low resolution, watermark
```

---

## Example 6: Image-to-Video

### User Input
> "我有一张山水画，想让画里的水流动起来"（with reference image attached）

### Output

## 🎬 Image-to-Video | Veo

> 📋 Model: Veo | Language: English | Suggested Length: 100-250 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | Traditional Chinese ink wash landscape painting, mountains and flowing river, maintaining the original brush stroke style and ink texture |
| **Scene** | Misty mountain landscape with cascading waterfall and winding river, maintaining the traditional painting atmosphere |
| **Camera** | Static camera with subtle slow zoom, maintaining full composition of the original painting |
| **Lighting** | Preserving the original ink wash tones, subtle light variations mimicking natural cloud movement |
| **Composition** | Maintaining exact composition of the reference image, no reframing |
| **Action/Emotion** | Gentle water flowing downstream, subtle waterfall mist rising, clouds slowly drifting between mountain peaks, leaves occasionally falling — serene and contemplative |
| **Quality** | High quality animation, maintaining ink wash painting texture, smooth natural motion, artistic style preservation |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Starting from the reference image, traditional Chinese ink wash landscape painting comes to life, gentle water flowing downstream with subtle ripples, waterfall mist slowly rising, clouds drifting between mountain peaks, occasional leaves falling, static camera with subtle slow zoom, preserving original brush stroke style and ink texture, serene contemplative atmosphere, smooth natural motion, maintaining style consistency with reference image, artistic quality, seamless loop
```

**Negative Prompt:**
```
style change, color shift, losing ink wash texture, photorealistic conversion, flickering, jittering, unnatural motion, morphing artifacts, temporal inconsistency, changing composition, adding new elements not in original
```

---

## Example 7: Text-to-Image

### User Input
> "赛博朋克风格的未来城市夜景"

### Output

## 🎬 Text-to-Image | Midjourney

> 📋 Model: Midjourney | Language: English | Suggested Length: 40-100 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | Towering futuristic skyscrapers with holographic advertisements, flying vehicles between buildings, neon-lit megastructures |
| **Scene** | Sprawling cyberpunk metropolis at night, rain-slicked streets reflecting neon lights, dense urban environment with layered infrastructure |
| **Camera** | Wide angle establishing shot from elevated perspective, looking down a neon-lit canyon of buildings |
| **Lighting** | Dramatic neon lighting in cyan, magenta, and purple, volumetric fog, wet surface reflections, strong rim lights on structures |
| **Composition** | Deep perspective with vanishing point, leading lines from building edges, layered depth with foreground rain drops |
| **Action/Emotion** | Dystopian yet mesmerizing, bustling metropolis energy frozen in a moment |
| **Quality** | Hyperrealistic digital art, 8K UHD, ultra-detailed, sharp focus, concept art quality, octane render |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Sprawling cyberpunk metropolis at night, towering futuristic skyscrapers with holographic advertisements, flying vehicles between buildings, neon-lit megastructures, rain-slicked streets reflecting cyan magenta and purple neon lights, dense urban environment with layered infrastructure, wide angle elevated perspective, deep vanishing point composition, volumetric fog, dramatic neon rim lighting, wet surface reflections, dystopian yet mesmerizing atmosphere, hyperrealistic digital art, concept art quality, 8K UHD, ultra-detailed, sharp focus, octane render
```

**Negative Prompt:**
```
low quality, blurry, pixelated, daytime, bright sunny, simple background, empty scene, watermark, text overlay, anime style, cartoon, low detail, flat lighting, no depth
```

---

## Example 8: Seedance Text-to-Video

### User Input
> "一只金色的猴子在丛林中跳跃，用 Seedance"

### Output

## 🎬 Text-to-Video | Seedance

> 📋 Model: Seedance | Language: Chinese | Suggested Length: 80-200 Chinese characters

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | "一只金色皮毛的猴子，琥珀色的眼眸，四肢敏捷" |
| **Scene** | "浓密的热带丛林树冠层，郁郁葱葱的绿色树叶间阳光穿透" |
| **Camera** | "跟拍镜头跟随猴子的运动轨迹，略带手持动感" |
| **Lighting** | "斑驳的自然阳光透过树冠洒落，温暖的热带色调，体积光" |
| **Composition** | "主体处于画面黄金分割点，树枝形成自然引导线" |
| **Action/Emotion** | "在树枝间欢快跳跃，灵活地荡秋千般移动，好奇而俏皮的表情" |
| **Quality** | "电影级质感，4K画质，动作流畅自然，主体一致性" |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
一只金色皮毛的猴子在浓密热带丛林的树枝间欢快跳跃，灵活地荡秋千般在树枝间移动，郁郁葱葱的绿色树叶间阳光穿透，跟拍镜头跟随猴子的运动轨迹，斑驳的自然阳光透过树冠洒落，温暖热带色调，好奇俏皮的表情，动作流畅，主体一致，电影级质感
```

**Negative Prompt:**
```
静止画面，模糊，低质量，主体不一致，闪烁，不自然运动，变形，多余肢体
```

---

## Example 9: Kling Text-to-Video

### User Input
> "一个宇航员在火星表面漫步，逃离感和孤独感，用 Kling"

### Output

## 🎬 Text-to-Video | Kling

> 📋 Model: Kling | Language: Chinese | Suggested Length: 80-200 Chinese characters

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
一位孤独的宇航员身穿风化的白色宇航服，在广袤的铁锈色火星地表缓慢行走，无尽的荒芜地平线延伸至远方，镜头缓慢后拉揭示巨大的虚无感，细微尘埃颗粒在稀薄大气中漂浮，强烈的侧光投下狭长的戏剧性阴影，去饱和的橙灰色调，孤寂沉郁的氛围，4K电影级质感，胶片质感，细节丰富高清
```

**Negative Prompt:**
```
拥挤场景，多人，绿色植被，地球天空，模糊，低质量，闪烁，欢快氛围，明亮色彩
```

---

## Example 10: Midjourney Text-to-Image

### User Input
> "一个奇幻风格的水晶塔，用 Midjourney"

### Output

## 🎬 Text-to-Image | Midjourney

> 📋 Model: Midjourney | Language: English | Suggested Length: 40-100 English words

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
majestic crystal tower rising from an enchanted forest, iridescent facets reflecting prismatic light, ethereal mist swirling at the base, bioluminescent flora climbing the structure, fantasy concept art, volumetric god rays, cool blue and warm amber color contrast, epic scale::2, intricate crystalline texture::1.5, wide angle dramatic perspective --ar 9:16 --style raw
```

**Negative Prompt:**
```
--no text, watermark, modern buildings, realistic photo, blurry, low detail
```

---

## Example 11: Nano Banana Text-to-Image

### User Input
> "一只橘猫趴在窗台上晒太阳"

### Output

## 🎬 Text-to-Image | Nano Banana

> 📋 Model: Nano Banana | Language: English | Suggested Length: 30-80 English words

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Orange tabby cat lounging on a sunlit windowsill, soft golden afternoon light, shallow depth of field, cozy domestic interior, warm tones, DSLR quality, peaceful sleepy expression, natural bokeh background
```

**Negative Prompt:**
```
blurry, low quality, distorted, extra limbs, cartoon, oversaturated, watermark
```

---

## Example 12: Hailuo Text-to-Video

### User Input
> "小女孩在雨中踩水坑，用海螺"

### Output

## 🎬 Text-to-Video | Hailuo

> 📋 Model: Hailuo | Language: Chinese | Suggested Length: 30-80 Chinese characters

---

> ℹ️ Hailuo model Prompt is concise and direct, 30-80 characters, no independent negative prompt supported

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
小女孩穿着雨靴在雨中用力踩水坑，水花四溅，开心大笑，清新活泼
```

---

## Example 13: Multi-Shot Narrative Mode

### User Input
> "拍一个咖啡店的短视频，先拍店门口，然后进入店内环境，最后拍一个拿铁拉花的特写"

### Output

## 🎬 Multi-Shot Narrative — Coffee Shop Short Video

> 📋 Model: Happy Horse | Mode: Multi-Shot Narrative | Language: Chinese | Shots: 3

### Shot Overview
| Shot # | Duration | Scale | Core Content |
|--------|----------|-------|--------|
| Shot 1 | 3s | Wide | Store exterior |
| Shot 2 | 4s | Medium | Interior environment |
| Shot 3 | 3s | Close-up | Latte art |

### 📝 Narrative Plan

**Transition Suggestions:**
- Shot 1 → Shot 2: Push-in connection (camera pushes through store door, natural transition to interior)
- Shot 2 → Shot 3: Quick cut (environment wide shot cuts to close-up detail, accelerating rhythm)

**Narrative Consistency:**
- Lighting continuity: Unified warm afternoon light
- Color palette: Warm brown, natural wood, cream white

---

### ✅ Shot Prompts (copy-ready)

**Shot 1 — Store Exterior:**
```
精致的咖啡小店外观，复古木质招牌，镜头从街道对面缓慢推进，晚秋午后暖阳洒在玄关花棵上，温馨文艺氛围
```

**Shot 2 — Interior Environment:**
```
咖啡店内部，原木吧台和开放式书架，镜头从入口平稳向前移动，柔和室内暖光，轻松惬意的日常氛围
```

**Shot 3 — Latte Art Close-up:**
```
咖啡师手持拉花缸在浓缩咖啡表面缓慢勾勒叶子图案，特写俶拍，柔和局部光，精致细节感
```

---

## Example 14: Prompt Variant Generation

### User Input
> "一匹白马在花田中奔跑，给我三个不同版本"

### Output

## 🎬 Text-to-Video — Prompt Variants

> 📋 Model: Happy Horse | Language: Chinese | Variants: Conservative / Creative / Minimal

### Conservative Version (Faithful to original description)
```
一匹白色骏马在盛开的花田中奔跑，镜头平移跟拍，午后自然光，鬃毛随风飘动，充满力量感
```

### Creative Version (Artistic divergence)
```
一匹通体雪白的骏马在薄暮的薰衣草花田中纵情奔驰，镜头从低角度仰拍跟随，金色的晚霞洒在马身上折射出光晕，花瓣被蹄声卷起在空中飞舞，如梦如幻的史诗感
```

### Minimal Version (Core elements only)
```
白马花田奔跑，跟拍，自然光
```

---

## Example 15: Runway Video Generation (English Prompt)

### User Input
> "帮我生成一个品牌宣传视频，一滴咖啡滴落到牛奶中激起漩涡，用 Runway"

### Output

## 🎬 Text-to-Video | Runway

> 📋 Model: Runway | Language: English | Suggested Length: 80-200 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | A single drop of dark espresso coffee |
| **Scene** | Macro close-up of cup interior, brand-premium studio environment |
| **Camera** | Macro close-up with shallow depth of field, smooth orbital camera movement |
| **Lighting** | Warm studio lighting from above, rich caramel and ivory color palette |
| **Composition** | Centered product focus, negative space around the drop for visual clarity |
| **Action/Emotion** | Falling in slow motion into creamy milk, creating elegant swirling patterns and fluid dynamics |
| **Quality** | Brand-premium aesthetic, cinematic quality, style-consistent |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
A single drop of dark espresso coffee falling in slow motion into a pool of creamy milk, creating elegant swirling patterns and fluid dynamics, warm studio lighting from above, macro close-up shot with shallow depth of field, smooth orbital camera movement around the cup, rich caramel and ivory color palette, brand-premium aesthetic, cinematic quality, style-consistent, professional commercial production
```

---

## Example 16: FLUX Image Generation (English Prompt)

### User Input
> "用 FLUX 生成一张赛博朋克风格的机械狐狸"

### Output

## 🎬 Text-to-Image | FLUX

> 📋 Model: FLUX Pro | Language: English | Suggested Length: 40-120 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | A mechanical fox made of polished brass gears and copper plates, intricate steampunk design |
| **Scene** | Perched on a pile of old leather-bound books, dark moody background with subtle steam wisps |
| **Lighting** | Warm tungsten key light from left, glowing amber eyes with tiny clockwork irises |
| **Style** | Victorian-era industrial aesthetic, photorealistic rendering |
| **Quality** | Highly detailed, sharp focus, 8K resolution |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
A mechanical fox made of polished brass gears and copper plates, intricate steampunk design, glowing amber eyes with tiny clockwork irises, Victorian-era industrial aesthetic, perched on a pile of old leather-bound books, warm tungsten key light from left, dark moody background with subtle steam wisps, highly detailed, sharp focus, 8K resolution, photorealistic rendering
```

**Negative Prompt:**
```
low quality, blurry, artifacts, distorted proportions, flat lighting, cartoonish, watermark, text, signature, oversaturated
```

---

## Example 17: Ideogram Poster Design (English Prompt)

### User Input
> "帮我用 Ideogram 做一张音乐节海报，标题是 ECHO FESTIVAL 2026"

### Output

## 🎬 Poster Design | Ideogram

> 📋 Model: Ideogram | Language: English | Suggested Length: 30-100 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Layout** | Music festival poster layout |
| **Text** | Bold headline text "ECHO FESTIVAL 2026" in modern geometric sans-serif font at the top |
| **Subject** | Abstract sound wave visualizations, silhouettes of crowd with raised hands |
| **Style** | Neon purple and electric blue gradient, vibrant contrast, editorial design |
| **Composition** | Clean negative space for event details, balanced composition |

---

> ℹ️ Quoted text "ECHO FESTIVAL 2026" will be accurately rendered in the image

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Music festival poster layout, bold headline text "ECHO FESTIVAL 2026" in modern geometric sans-serif font at the top, abstract sound wave visualizations flowing across the background, neon purple and electric blue gradient, silhouettes of crowd with raised hands at the bottom, clean negative space for event details, vibrant contrast, professional print quality, balanced composition, editorial design
```

**Negative Prompt:**
```
blurry text, illegible typography, cluttered layout, poor contrast, amateur design, overcrowded elements
```

---

## Example 18: Physical Plausibility Correction (Kling Text-to-Video)

### User Input
> "一个武术高手悬停在空中一动不动30秒，用Kling"

### Output

## 🎬 Text-to-Video | Kling

> 📋 Model: Kling | Language: Chinese | Suggested Length: 80-200 Chinese characters

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | "一位身着白色练功服的武术高手，神态沉稳" |
| **Scene** | "空旷的山顶练功场，云雾缭绕" |
| **Camera** | "低角度仰拍，慢速推进至中景" |
| **Lighting** | "侧逆光，清晨金色光线穿透薄雾" |
| **Composition** | "主体居中偏左，右侧留白展现空间纵深感，云雾形成自然层次" |
| **Action/Emotion** | "以极速慢动作（240fps降速播放）跃入空中，在最高点短暂滞留约1-2秒，衣袂微微飘动，展现极致控制力" |
| **Quality** | "4K电影级质感，胶片颗粒感，高清细节，专业武术摄影风格" |

---

### 📝 Notes

> ⚠️ **Physical Plausibility Correction**
> - **Issue**: "用户原始描述'悬停在空中一动不动30秒'违反物理定律——人类无法在无外力作用下长时间悬浮于空中"
> - **Fix**: "改为'极速慢动作跳跃至最高点短暂滞留1-2秒'，在视觉上呈现类似悬浮效果，同时保持物理合理性"
> - **Remaining Limitation**: "Kling 单次生成建议不超过5秒，30秒需拆分为多段生成"

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
一位身着白色练功服的武术高手在云雾缭绕的山顶练功场纵身跃起，以极速慢动作在空中划出优美弧线，在最高点短暂滞留约两秒，衣袂在气流中微微飘动，展现极致的身体控制力与内力，低角度仰拍缓慢推进，侧逆光清晨金色光线穿透薄雾，沉稳而强大的气场，4K电影级质感，胶片质感，细节丰富高清
```

**Negative Prompt:**
```
模糊，低质量，闪烁，变形，多余肢体，不自然运动，静止悬停超过2秒
```

---

## Example 19: Pika Text-to-Video (Creative Effects)

### User Input
> "A chocolate bar melting into a river of liquid gold, use Pika"

### Output

## 🎬 Text-to-Video | Pika

> 📋 Model: Pika | Language: English | Suggested Length: 60-150 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | A premium dark chocolate bar with gold foil wrapper partially unwrapped |
| **Scene** | Clean studio background with warm ambient lighting, reflective surface beneath |
| **Camera** | Macro close-up with smooth orbital movement, shallow depth of field |
| **Lighting** | Warm studio lighting from above, rich caramel and gold color palette |
| **Composition** | Centered product focus, negative space around the subject for visual clarity |
| **Action/Emotion** | The chocolate bar slowly melts and transforms into a flowing river of liquid gold, creating elegant swirling patterns and fluid dynamics |
| **Quality** | Premium commercial aesthetic, cinematic macro quality, smooth motion, brand-luxury feel |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
A premium dark chocolate bar with gold foil wrapper slowly melting and transforming into a flowing river of liquid gold, creating elegant swirling patterns and fluid dynamics, macro close-up shot with shallow depth of field, smooth orbital camera movement, warm studio lighting from above, rich caramel and gold color palette, premium commercial aesthetic, cinematic quality, brand-luxury feel, seamless morph transition
```

**Negative Prompt:**
```
low quality, blurry, pixelated, flickering, jittering, abrupt transitions, unnatural motion, watermark
```

---

## Example 20: Recraft Image Generation (Vector Graphics)

### User Input
> "Design a minimalist vector logo for a coffee brand called 'BREW', use Recraft"

### Output

## 🎬 Text-to-Image | Recraft

> 📋 Model: Recraft | Language: English | Suggested Length: 30-100 English words

---

### 💡 Creative Analysis

| Component | Content |
|-----------|---------|
| **Subject** | Minimalist coffee cup icon integrated with the wordmark "BREW" |
| **Scene** | Clean white background, no environmental elements |
| **Camera** | Flat graphic perspective, front-facing icon view |
| **Lighting** | Flat color fills, no gradients or shadows, clean graphic style |
| **Composition** | Icon centered above wordmark, balanced vertical stack layout, generous padding |
| **Action/Emotion** | Static logo design, conveying warmth, craft, and premium quality |
| **Quality** | Vector output, SVG format, scalable, professional brand design quality |

---

### ✅ Final Prompt

> The following is the complete Prompt ready for direct copy-paste:

**Positive Prompt:**
```
Minimalist vector logo design featuring a simple coffee cup icon with a subtle steam curl, integrated with the wordmark "BREW" in clean modern sans-serif typography, flat color fills in warm espresso brown and cream, no gradients or shadows, clean white background, balanced vertical stack layout, SVG vector output, scalable professional brand design, minimalist aesthetic, craft coffee identity
```

**Negative Prompt:**
```
photorealistic, complex details, gradients, shadows, 3D rendering, cluttered elements, multiple colors, busy background
```
