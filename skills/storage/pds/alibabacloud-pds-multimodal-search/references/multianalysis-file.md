# PDS Document and Audio/Video Analysis

**Scenario**: When you have obtained the drive_id, file_id, and revision_id of the file to analyze and need to perform analysis on that file
**Purpose**: Perform analysis on files and get structured analysis results
---

## Core Workflow

### Flow 1: Submit Analysis Task and Poll for Results

Use Python script to automatically submit analysis task and poll until processing is complete.

```bash
# Document analysis polling
python scripts/pds_poll_processor.py \
  --drive-id "1" \
  --file-id "66e7e860a2360204b9414d5c866dd3a20af1974e" \
  --revision-id "123" \
  --x-pds-process "doc/analysis" \
  -o doc_result.json

# Audio/Video analysis polling
python scripts/pds_poll_processor.py \
  --drive-id "1" \
  --file-id "66e7e860a2360204b9414d5c866dd3a20af1974e" \
  --revision-id "123" \
  --x-pds-process "video/analysis" \
  -o video_result.json
```

**Parameter Description**:
- `--drive-id`: The space `drive_id` where the analysis file is located
- `--file-id`: The `file_id` of the file to analyze
- `--revision-id`: The `revision_id` of the file to analyze
- `--x-pds-process`: Processing type, `doc/analysis` (document) or `video/analysis` (audio/video). Since analysis is a synchronous API, x-pds-process must be used, not x-pds-async-process
- `-o`: Save raw JSON result to file (contains signed URLs)

#### Document Analysis Result Structure

```json
{
  "summary": ["https://bucket/summary.json?sign=xxx"],
  "chapter_summaries": ["https://bucket/chapter_summaries.json?sign=xxx"],
  "keywords": ["https://bucket/keywords.json?sign=xxx"],
  "guiding_questions": ["https://bucket/guiding_questions.json?sign=xxx"],
  "method_description": ["https://bucket/method_description.json?sign=xxx"],
  "experiment_description": ["https://bucket/experiment_description.json?sign=xxx"],
  "conclusion_description": ["https://bucket/conclusion_description.json?sign=xxx"],
  "images": {
    "imgs/page_0_img_image_box_770_540_1367_860.png": {
      "Url": "https://bucket/imgs/page_0_img.png?sign=xxx",
      "Thumbnail": "https://bucket/imgs/page_0_img_thumbnail.png?sign=xxx"
    }
  }
}
```

#### Audio/Video Analysis Result Structure

```json
{
  "markdown": "https://bucket/markdown.md?sign=xxx",
  "summary": ["https://bucket/summary.json?sign=xxx"],
  "chapter_summaries": ["https://bucket/chapter_summary.json?sign=xxx"],
  "keywords": ["https://bucket/keywords.json?sign=xxx"],
  "questions": ["https://bucket/questions.json?sign=xxx"],
  "transcript": ["https://bucket/transcript.json?sign=xxx"],
  "transcript_summaries": ["https://bucket/transcript_summary.json?sign=xxx"],
  "transcript_chapter_summaries": ["https://bucket/transcript_chapter_summary.json?sign=xxx"],
  "ppt_details": ["https://bucket/ppt_details.json?sign=xxx"],
  "images": {
    "ppts/video_snapshots_0.jpg": {
      "Url": "https://bucket/ppts/video_snapshots_0.jpg?sign=xxx",
      "Thumbnail": "https://bucket/ppts/video_snapshots_0_thumbnail.jpg?sign=xxx"
    }
  }
}
```


### Flow 2: Use Formatter to Get Formatted Results

Analysis results contain multiple signed URLs pointing to different types of analysis files. Use formatting scripts to parse these files and generate readable output.

```bash
# Format document results
python scripts/doc_analysis_formatter.py doc_result.json -o formatted_output.txt

# Format audio/video results
python scripts/video_analysis_formatter.py video_result.json -o formatted_output.txt
```

**Parameter Description**:
- `input_file`: JSON result file path from analysis API (output from Flow 1)
- `-o`: Formatted output file path (optional, outputs to console if not specified)

#### Formatted Output Example

The formatting script automatically downloads all files pointed to by signed URLs and generates readable output according to preset templates:

````

==================================================
📄 【Full Summary】
==================================================

{Summary text content}

🖼️ Image: {ImagePath} (Page {PageNumber})

==================================================
🏷️ 【Keywords】
==================================================
#{Keyword 1} | #{Keyword 2} | #{Keyword 3} | ...

==================================================
📚 【Chapter Summaries】
==================================================

▶️ {Chapter Title}
----------------------------------------
  {Chapter Content}

  🖼️ Image: {ImagePath}

▶️ {Next Chapter Title}
----------------------------------------
  ...

==================================================
❓ 【Guiding Questions】
==================================================

Q1: {Question 1}
A1: {Answer 1}

Q2: {Question 2}
A2: {Answer 2}
````

Audio/video will also include dialogue transcripts and PPT extraction information.

---

### Flow 3: Extract PPT from Video

If the analyzed video contains PPT, you can extract PPT from the results and generate a PPTX file.

#### Prerequisites

1. Video contains PPT content
2. Analysis results contain `ppt_details` field
3. Install Python PPT processing library

```bash
pip install python-pptx requests
```

#### Usage

Extract PPT from video analysis results and generate PPTX file:

```bash
python scripts/ppt_extraction.py video_result.json -o extracted_ppt.pptx
```

**Parameter Description**:
- `input_file`: JSON result file path from video analysis API
- `-o`: Output PPTX file path (default: extracted_ppt.pptx)
- `--keep-aspect-ratio`: Maintain image aspect ratio (default fills entire slide)
- `--validate`: Validate PPTX file after generation



##### Checklist

- [ ] PPTX file can be opened with PowerPoint/WPS/LibreOffice
- [ ] Slide count matches page count in `ppt_details`
- [ ] Each page image is clear, no stretching or distortion
- [ ] Page order matches appearance order in video
- [ ] (Optional) Notes contain timestamp information

##### Auto Validation

```bash
python scripts/ppt_extraction.py video_result.json --validate
```

#### Common Issues

##### 1. Feature Not Enabled
```json
{
  "code": "OperationNotSupport",
  "message": "This operation is not supported."
}
```
**Solution**: Contact PDS technical support to enable analysis feature.


##### 2. Signed URL Expired

**Cause:** Download took too long, signed URL has expired.

**Solution:** Re-request analysis results, or download all images immediately after getting results.