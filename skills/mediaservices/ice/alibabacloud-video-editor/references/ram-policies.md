# RAM Policies for alibabacloud-video-editor

This document lists the RAM permissions required to use this Skill.

## Required Permissions

### ICE (Intelligent Media Services) Permissions

Editing and synthesis:

- `ice:SubmitMediaProducingJob` — Submit media editing and synthesis tasks
- `ice:GetMediaProducingJob` — Query media editing and synthesis task status
- `ice:GetMediaInfo` — Get media information (used to obtain the authenticated URL of the output video)

Reading the material (SKILL.md §2 workflow step 4 — required for every multi-clip edit):

- `ice:SubmitASRJob` — Submit a speech-recognition job for the dialogue timeline
- `ice:GetSmartHandleJob` — Read the result of a smart job (serves ASR, TextToSpeech, TextGenerate)
- `ice:SubmitSnapshotJob` — Submit a snapshot job for frames / filmstrip / WebVTT
- `ice:GetSnapshotJob` — Query snapshot job state
- `ice:GetSnapshotUrls` — Read the generated snapshot URLs

Single-media algorithms:

- `ice:SubmitIProductionJob` — Submit intelligent production (single-media algorithm) tasks
- `ice:QueryIProductionJob` — Query intelligent production task status and results

Templates:

- `ice:CreateCustomTemplate` — Create a custom snapshot template (Type 2)
- `ice:ListCustomTemplates` — List templates (used to reuse an existing snapshot template)
- `ice:AddTemplate` — Create a persistent normal Timeline template
- `ice:GetTemplate` — Read a normal template Config and ClipsParam contract

Project export:

- `ice:SubmitProjectExportJob` — Submit a project export task (the AI-expanded timeline)
- `ice:GetProjectExportJob` — Query a project export task and read the exported timeline

### OSS (Object Storage Service) Permissions

If you need to upload local materials to OSS, the following permissions are also required:

- `oss:PutObject` — Upload files to OSS
- `oss:GetObject` — Read OSS files
- `oss:ListBuckets` — List Buckets (used to select the output Bucket)

## Recommended System Policies

You can choose to use the following system policies for quick authorization:

- `AliyunICEFullAccess` — Full access permissions for ICE service
- `AliyunOSSFullAccess` — Full access permissions for OSS service (if OSS upload functionality is required)

## Minimum Permission Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ice:SubmitMediaProducingJob",
        "ice:GetMediaProducingJob",
        "ice:GetMediaInfo",
        "ice:SubmitASRJob",
        "ice:GetSmartHandleJob",
        "ice:SubmitSnapshotJob",
        "ice:GetSnapshotJob",
        "ice:GetSnapshotUrls",
        "ice:SubmitIProductionJob",
        "ice:QueryIProductionJob",
        "ice:CreateCustomTemplate",
        "ice:ListCustomTemplates",
        "ice:SubmitProjectExportJob",
        "ice:GetProjectExportJob",
        "ice:AddTemplate",
        "ice:GetTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

## Official RAM Documentation

- [RAM User Authorization Documentation](https://help.aliyun.com/zh/ims/user-guide/create-and-authorize-a-ram-user-1)
- [ICE API Reference](https://help.aliyun.com/zh/ims/developer-reference/) — each Action's page names the RAM permission it requires
