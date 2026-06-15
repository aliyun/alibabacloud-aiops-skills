"""
Minimal driving-video image labeling + image embedding job.

Reads an ODPS image table whose `image_url` column points at OSS-hosted
images, runs multi-modal labeling and image embedding via AI FUNC, and
writes one row per image to an output table.

Required env vars:
- ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, ODPS_ENDPOINT
- OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET   passed to `cp.image(...,
  storage_options=...)` so the AI FUNC inference service can fetch the
  OSS-hosted images. The AI FUNC call needs the OSS credentials
  inline; `role_arn` is not a substitute on this code path.
- MODEL_PROJECT (typically `bigdata_public_modelset`), VLM_MODEL,
  EMBEDDING_MODEL
- IMAGE_INPUT_TABLE, OUTPUT_TABLE

AI FUNC (`model.generate` / `model.embed`) calls Aliyun's built-in
Bailian / ModelStudio inference; the operator does not need GPU quota
nicknames. `running_options` should carry behavior knobs only
(`enable_thinking`, `enable_real_rpm_stats`, `verbose`).

The catalog endpoint that `read_odps_model` needs is derived from the
ODPS handle via `o.get_catalog_host()` and applied to the PyODPS global
option `odps_options.catalog.endpoint` -- no extra env var.
"""

import json
import os

import dotenv
import pandas as pd
from odps import ODPS
from odps import options as odps_options

import maxframe.dataframe as md
from maxframe.learn.contrib.llm import ContentPart, ImageContentType
from maxframe.learn.utils import read_odps_model
from maxframe.session import new_session

dotenv.load_dotenv()

MODEL_PROJECT = os.environ["MODEL_PROJECT"]
VLM_MODEL = os.environ["VLM_MODEL"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]

OSS_ACCESS_KEY_ID = os.environ["OSS_ACCESS_KEY_ID"]
OSS_ACCESS_KEY_SECRET = os.environ["OSS_ACCESS_KEY_SECRET"]

IMAGE_INPUT_TABLE = os.environ["IMAGE_INPUT_TABLE"]
OUTPUT_TABLE = os.environ["OUTPUT_TABLE"]
IMAGE_URL_COL = os.getenv("IMAGE_URL_COL", "image_url")
IMAGE_ID_COL = os.getenv("IMAGE_ID_COL", "image_id")

LABEL_PROMPT = os.getenv(
    "LABEL_PROMPT",
    "Annotate this driving-scene frame. Output strict JSON with fields: "
    "scene_type, weather, key_objects, risk_level.",
)

# OSS credentials for the AI FUNC inference service to fetch the OSS
# image URLs. Passed via `storage_options=` on every `cp.image(...)`
# call -- the service runs in its own context and cannot rely on the
# caller's role_arn.
STORAGE_OPTIONS = {
    "access_key_id": OSS_ACCESS_KEY_ID,
    "access_key_secret": OSS_ACCESS_KEY_SECRET,
}

# Behavior knobs for AI FUNC LLM calls. `enable_thinking=False` is the
# important one for Qwen3 reasoning models (qwen3.6-plus etc.), which
# CoT-reason by default and would otherwise pollute the response
# content with the reasoning trace. `enable_real_rpm_stats` surfaces
# rate-limit telemetry on the server side. AI FUNC = MaxFrame's
# built-in Bailian inference; it does not need GPU / inference quota
# nicknames here.
GENERATE_RUN_OPTS = {"enable_thinking": False, "enable_real_rpm_stats": True}
EMBED_RUN_OPTS = {"enable_real_rpm_stats": True}


def _parse_response(chunk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in chunk.iterrows():
        base = {
            IMAGE_ID_COL: r[IMAGE_ID_COL],
            IMAGE_URL_COL: r[IMAGE_URL_COL],
            "label_text": None,
            "label_input_token": 0,
            "label_output_token": 0,
            "image_embedding": None,
            "image_embedding_total_token": 0,
            "status": "ok",
            "error_stage": "",
            "error_msg": "",
        }

        if not r["label_success"]:
            base.update(
                status="failed",
                error_stage="label",
                error_msg=str(r["label_response"])[:512],
            )
            rows.append(base)
            continue

        try:
            label_resp = json.loads(r["label_response"]) if isinstance(r["label_response"], str) else r["label_response"]
            base["label_text"] = label_resp["choices"][0]["message"]["content"]
            usage = label_resp.get("usage", {}) or {}
            base["label_input_token"] = int(usage.get("prompt_tokens", 0) or 0)
            base["label_output_token"] = int(usage.get("completion_tokens", 0) or 0)
        except Exception as exc:
            base.update(status="failed", error_stage="label", error_msg=f"label_parse: {exc}")
            rows.append(base)
            continue

        if not r["image_embedding_success"]:
            base.update(
                status="failed",
                error_stage="image_embedding",
                error_msg=str(r["image_embedding_response"])[:512],
            )
            rows.append(base)
            continue

        try:
            emb_resp = json.loads(r["image_embedding_response"]) if isinstance(r["image_embedding_response"], str) else r["image_embedding_response"]
            base["image_embedding"] = json.dumps(emb_resp["output"]["embeddings"][0]["embedding"])
            usage = emb_resp.get("usage", {}) or {}
            base["image_embedding_total_token"] = int(usage.get("total_tokens", 0) or 0)
        except Exception as exc:
            base.update(status="failed", error_stage="image_embedding", error_msg=f"emb_parse: {exc}")

        rows.append(base)
    return pd.DataFrame(rows)


def main():
    o = ODPS(
        access_id=os.environ["ODPS_ACCESS_ID"],
        secret_access_key=os.environ["ODPS_ACCESS_KEY"],
        project=os.environ["ODPS_PROJECT"],
        endpoint=os.environ["ODPS_ENDPOINT"],
    )

    # Derive the catalog endpoint from the ODPS handle and apply it to the
    # PyODPS global option. `read_odps_model` consults this global to build
    # the full `http://<host>/api/catalog/v1alpha/...` URL when calling
    # `model.reload()`. Without this line PyODPS raises `MissingSchema: Invalid
    # URL 'oxs/api/catalog/...'` error because PyODPS only has the host
    # ('oxs' or 'catalogapi.<region>.maxcompute.aliyun.com') and no scheme.
    odps_options.catalog.endpoint = f"http://{o.get_catalog_host()}"

    session = new_session(o)
    print(f"Logview: {session.get_logview_address()}")

    try:
        df = md.read_odps_table(IMAGE_INPUT_TABLE)
        df = df[[IMAGE_ID_COL, IMAGE_URL_COL]]

        vlm = read_odps_model(VLM_MODEL, project=MODEL_PROJECT)
        emb_model = read_odps_model(EMBEDDING_MODEL, project=MODEL_PROJECT)

        cp = vlm.content_part

        label_df = vlm.generate(
            df,
            messages=[
                {
                    "role": "user",
                    "content": [
                        cp.text(LABEL_PROMPT),
                        cp.image(
                            data=df[IMAGE_URL_COL],
                            type=ImageContentType.IMAGE_URL,
                            storage_options=STORAGE_OPTIONS,
                        ),
                    ],
                }
            ],
            simple_output=False,
            params={"max_tokens": 1024},
            running_options=GENERATE_RUN_OPTS,
        )

        emb_df = emb_model.embed(
            df,
            input=[
                cp.image(
                    data=df[IMAGE_URL_COL],
                    type=ImageContentType.IMAGE_URL,
                    storage_options=STORAGE_OPTIONS,
                ),
            ],
            simple_output=False,
            params={"timeout": 120},
            running_options=EMBED_RUN_OPTS,
        )

        combined = md.concat(
            [
                df,
                label_df.rename(
                    columns={"response": "label_response", "success": "label_success"}
                ),
                emb_df.rename(
                    columns={
                        "response": "image_embedding_response",
                        "success": "image_embedding_success",
                    }
                ),
            ],
            axis=1,
        )

        result = combined.mf.apply_chunk(
            _parse_response,
            output_type="dataframe",
            dtypes=pd.Series(
                {
                    IMAGE_ID_COL: "object",
                    IMAGE_URL_COL: "object",
                    "label_text": "object",
                    "label_input_token": "int64",
                    "label_output_token": "int64",
                    "image_embedding": "object",
                    "image_embedding_total_token": "int64",
                    "status": "object",
                    "error_stage": "object",
                    "error_msg": "object",
                }
            ),
        )

        md.to_odps_table(result, OUTPUT_TABLE, overwrite=True).execute()
    finally:
        session.destroy()


if __name__ == "__main__":
    main()
