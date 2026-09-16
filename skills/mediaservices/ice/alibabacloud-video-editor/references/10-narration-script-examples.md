# Narration Script Examples

When customizing a 2D simulated digital human, or when filling the `Content` of `AI_TTS` clips / `AI_Avatar` clips, models can read these example scripts (or a familiar script of their own) to record/synthesize narration. These examples show the tone and structure of two common narration styles.

The excerpts below are verbatim sample data to be copied into `Content`, not documentation prose.

## Example 1: Story Commentary

A culture-program style commentary on *Strange Tales from a Chinese Studio*. Structure: open with the topic → introduce the work and its value → examine one representative supernatural romance → analyze characters and themes → broaden to cultural influence and legacy → closing.

Excerpt (opening):

```text
Today, we are exploring a classic work of Chinese literature: Strange Tales from a Chinese Studio. Written by Pu Songling during the Qing dynasty, this collection brings together stories of spirits, monsters, and the supernatural that helped shape classical Chinese fantasy.

Its stories are rich in imagination while also reflecting Qing society and everyday life. Their plots range from playful and humorous to thoughtful explorations of human nature and moral choices.
```

Excerpt (story deep-dive):

```text
One memorable tale follows a young woman who meets a scholar in a dream garden. They fall in love at first sight but struggle to reunite in the waking world. Their story uses romance and the supernatural to explore longing, devotion, and the boundary between dreams and reality.
```

Excerpt (closing):

```text
In conclusion, Strange Tales from a Chinese Studio remains an important cultural work. Through imaginative stories and sharp observations, it reveals the enduring appeal and wisdom of traditional Chinese culture. Thank you for joining this episode, and we look forward to seeing you again next time.
```

Style notes: long-form, literary, reflective; suitable for commentary or newscast voices such as `zhilun`, `zhide`, and `zhiru`, or CosyVoice audiobook voices such as `longshu`.

## Example 2: Live Commerce

A product-pitch script for an eye-cream set. Structure: thank the audience + pain point → product introduction (two products, each with ingredients and effects) → target audience → usage instructions → price / promotion / stock urgency → consultation channel → closing thanks.

Excerpt (opening + pain point):

```text
Hello everyone, and thank you for supporting our live stream! Today I am introducing a professional eye-cream set designed to address fine lines, dark circles, and puffiness. As the delicate skin around the eyes changes with age, choosing a high-quality care set can make a noticeable difference.
```

Excerpt (product detail):

```text
First, let us look at the daily eye cream. It contains botanical extracts and collagen to firm the skin, soften the appearance of fine lines and puffiness, and improve elasticity and radiance. Its lightweight texture absorbs quickly and feels comfortable throughout the day.
```

Excerpt (price + urgency):

```text
During this live stream, the complete set is available for only CNY 198. The first thirty customers will also receive a complimentary gift, making this an excellent value. Stock is limited, so add the set to your cart and check out now to claim the offer.
```

Excerpt (closing):

```text
Thank you for watching today. We hope this set helps your eye area look brighter, smoother, and more refreshed. We look forward to shipping your order soon and giving you a high-quality skincare experience. Thank you again for your support!
```

Style notes: conversational, persuasive, interactive; suitable for live-streaming / hawking voices (e.g. `zhiyan_emo`, `laomei`, `qiaowei`, `maoxiaomei`, `ailun`) or CosyVoice live-commerce voices (e.g. `loongstella`).

## Usage Tips

- Put the chosen script into `AI_TTS` / `AI_Avatar` `Content`. Long scripts can be wrapped in SSML to add pauses (`<break>`), number reading rules (`<say-as>`), etc.
- Match the voice to the script style: each example's Style notes above name the voices that suit it.
- For avatar narration the synthesized speech must be at least 1 second long; the avatar output is fixed 9:16 / 1080×1920 / 4000 kb/s.
