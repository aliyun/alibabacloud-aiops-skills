# M3: Compliance / Security-Qualification Materials - Who Provides What

Use this module for capability **S2**: when the customer asks for "the
compliance certificate", "security qualification materials", "proof
documents", or "the Dengbao filing certificate" for their audit.

## Evidence provenance (read first)

No official self-service download-channel page was verified for this skill's
tier during development, and no support-ticket evidence was injected. The
channel list below is therefore deliberately a **placeholder with a DEGRADED
protocol**: give responsibility-split facts (stable), and state the pending
status verbatim (unstable part). NEVER invent or guess download links, file
names, or "what you should find there" claims.

## Material buckets and responsibility owners

| Bucket | Typical customer wording | Who issues / owns it | How it is obtained |
|---|---|---|---|
| A. Platform-side qualification evidence | "Alibaba Cloud's compliance certificates / security qualifications / the platform's Dengbao filing materials" | The cloud platform publishes qualification and compliance materials for its infrastructure and services | Self-service through the official website's compliance/qualifications area and the help portal; exact in-product channel links for this tier are **pending human verification** (see protocol below) |
| B. Customer-system assessment report | "our level 3 report", "the assessment certificate for our system" | An accredited assessment body, after assessing the CUSTOMER's own information system; filing records are handled by the customer with the local cybersecurity authority | Contract an assessment body; the platform role is to provide inherited-capability evidence (Bucket A) and configuration evidence (this skill's S3 inventory) |
| C. Legal-grade / bespoke documents | "stamped original", "paper copy", "NDA / confidentiality agreement", "custom attestation letter" | Commercial / legal channel | Human support / business contact via a support ticket; the skill only routes, it never promises content, wording, or timing |

## DEGRADED protocol for Bucket A (mandatory wording discipline)

When the customer asks where to download Bucket-A materials:

1. State plainly: "the verified official channel for this specific material
   is not available in this skill's knowledge yet", then point to the
   generic self-service path: the Alibaba Cloud official website and the
   help portal search (search terms: Dengbao, classified protection,
   compliance certificate, qualifications) - `https://help.aliyun.com` is
   the portal root, and no deeper URL may be cited until verified.
2. Recommend opening a support ticket if the audit needs a specific stamped
   or named file - that is Bucket C, always human.
3. End the answer with `STATUS: DEGRADED` semantics: what was answered
   (responsibility split, bucket classification) vs. what is pending
   (verified channel links).

## What the skill must NOT claim

- That any particular certificate "covers" the customer's system, or that
  platform-level qualification implies the customer's own compliance (see M2
  responsibility split).
- The existence, name, or format of a specific downloadable file.
- Legal validity, signing, stamping, or acceptance by a local authority.
- Any timeline for assessment approval or filing outcomes.

## Bridge to the read-only inventory (Bucket B support)

Assessors sample the customer's real assets. The S3 inventory output
(instances, bound security groups, states per named region; see M4 and the
entry script) plus the manual checklist gives the customer a factual,
reproducible starting point for their own evidence pack. Re-run the same
command before the assessment to refresh it; the report is conversational
output only - this skill writes nothing to disk and changes nothing in the
account.
