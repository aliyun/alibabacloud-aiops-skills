#!/usr/bin/env python3
"""
Yunxiao Flow Pipeline Troubleshooting Tool

Usage:
    python yunxiao_flow_get_pipeline_runs.py --org-id <Organization ID> --pipeline-id <Pipeline ID> --token <Access Token> --pipeline-runid <Run ID> [--domain <Domain>]
"""
import copy
import os
import platform

# Detect if running on macOS
if platform.system() == 'Darwin':
    os.environ['SSL_CERT_DIR'] = '/private/etc/ssl/certs'   # Certificate directory
    os.environ['SSL_CERT_FILE'] = '/private/etc/ssl/cert.pem'   # Certificate file

import argparse
import json
import urllib.request
import urllib.error


def mask_token(token):
    """Mask token for display, showing first 6 and last 6 characters with ******* in between"""
    if not token or len(token) <= 12:
        return '***'
    return f"{token[:6]}*******{token[-6:]}"


def deep_parse_json_strings(data):
    """
    Recursively traverse data structure, converting all JSON-like strings to actual JSON objects/lists.
    Supports multi-level nested JSON string parsing.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # Recursively process dict values
            new_dict[key] = deep_parse_json_strings(value)
        return new_dict

    elif isinstance(data, list):
        # Recursively process each element in list
        return [deep_parse_json_strings(item) for item in data]

    elif isinstance(data, str):
        # Try to parse string as JSON
        try:
            # Strip whitespace to prevent parsing failures
            stripped = data.strip()
            if not stripped:
                return data

            parsed = json.loads(stripped)

            # Key point: after successful parsing, must recursively call self again!
            # Because the parsed object may contain another layer of JSON strings
            return deep_parse_json_strings(parsed)

        except (json.JSONDecodeError, TypeError):
            # If not a valid JSON string or parsing fails, keep original
            return data

    else:
        # Other types (int, float, bool, None) return as-is
        return data


def get_pipeline_job_steps(org_id, pipeline_id, pipeline_runid, job_id, token, domain):
    """Get step details under a job for a specific pipeline run"""
    if "openapi-rdc.aliyuncs.com" == domain:
        url = f"https://{domain}/oapi/v1/flow/organizations/{org_id}/pipelines/{pipeline_id}/pipelineRuns/{pipeline_runid}/jobs/{job_id}/steps"
    else:
        url = f"https://{domain}/oapi/v1/flow/pipelines/{pipeline_id}/pipelineRuns/{pipeline_runid}/jobs/{job_id}/steps"

    req = urllib.request.Request(url)
    req.add_header('x-yunxiao-token', token)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp = json.loads(response.read().decode('utf-8'))
            # Convert job params from string to json
            return resp

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "body": e.read().decode('utf-8') if e.fp else None}
    except Exception as e:
        return {"error": str(e)}



def get_pipeline_runs(org_id, pipeline_id, pipeline_runid, token, domain):
    """Get pipeline run details by calling GetPipelineRun"""
    if "openapi-rdc.aliyuncs.com"==domain:
        url = f"https://{domain}/oapi/v1/flow/organizations/{org_id}/pipelines/{pipeline_id}/runs/{pipeline_runid}"
    else:
        url = f"https://{domain}/oapi/v1/flow/pipelines/{pipeline_id}/runs/{pipeline_runid}"
    
    req = urllib.request.Request(url)
    req.add_header('x-yunxiao-token', token)
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp = json.loads(response.read().decode('utf-8'))
            # Convert job params from string to json
            stages = resp['stages']
            for stage in stages:
                for job in stage['stageInfo']['jobs']:
                    if job['params']:
                        params = deep_parse_json_strings(job['params'])
                        job['params'] = params

                    if job['result']:
                        result = deep_parse_json_strings(job['result'])
                        job['result'] = result

            return resp

    except urllib.error.HTTPError as e:
        print({"error": f"HTTP {e.code}: {e.reason}", "body": e.read().decode('utf-8') if e.fp else None})
        exit(1)
    except Exception as e:
        print({"error": str(e)})
        exit(1)


def get_new_flow_info(resp, token):
    """Restore pipeline step information based on GetPipelineRun response"""
    flow = {
        "org_id": resp['org_id'],
        "pipelineId": resp['pipelineId'],
        "pipelineRunId": resp['pipelineRunId'],
        "status": resp['status'],
        "stageGroup": resp['stageGroup'],
        "groups": resp['groups'],
        "pipelineType": resp['pipelineType'],  # Pipeline type
    }
    # Extract steps from each job for later aggregation
    job_step = {}
    for stage in resp['stages']:
        for job in stage['stageInfo']['jobs']:
            if job['params'] and job['params'].get('steps'):
                job_step[job['id']] = copy.deepcopy(job['params']['steps'])
            else:
                job_step[job['id']] = None
            
            
    new_stages = []
    for stage in resp['stages']:
        one_stage = {
            "name": stage['name'],
            "status": stage['stageInfo']['status'],
            "id": stage['stageInfo']['id'],
            "stage_index": stage['index']
        }
        jobs = []
        for job in stage['stageInfo']['jobs']:
            new_job = {
                "id": job['id'],
                "name": job['name'],
                "status": job['status'],
                "startTime": job['startTime'],
                "endTime": job['endTime']
            }

            if job['startTime'] is None:
                new_job['steps'] = []
            else:
                resp_steps = get_pipeline_job_steps(
                    resp['org_id'],
                    resp['pipelineId'],
                    resp['pipelineRunId'],
                    job['id'],
                    token,
                    resp['domain']
                )
                if isinstance(resp_steps, list) and len(resp_steps)>0:
                    if resp_steps[0].get('buildProcessNodes'):
                        new_job['steps'] = resp_steps[0]['buildProcessNodes']

                    # Merge steps parameters with run results
                    for step_tmp in new_job['steps']:
                        if step_tmp['stepName'].startswith('申请运行环境(') or step_tmp['stepName'].startswith('克隆代码(') or step_tmp['stepName'].startswith('流水线缓存(') or step_tmp['stepName'].startswith('缓存上传('):
                            continue
                        for param_step in job_step[job['id']]:
                            if step_tmp['stepName'].startswith(param_step['name']):
                                step_tmp.update(param_step)

                else:
                    new_job['steps'] = resp_steps

            if job.get('params'):
                params = copy.deepcopy(job['params'])
                if params.get('steps'):
                    del params['steps']
            else:
                params = None

            result = copy.deepcopy(job['result']) if job.get('result') else None
            actions = copy.deepcopy(job['actions']) if job.get('actions') else None
            new_job['params'] = params
            new_job['result'] = result
            new_job['actions'] = actions
            jobs.append(new_job)
        one_stage['jobs'] = jobs
        new_stages.append(one_stage)

    flow['stages'] = new_stages

    return flow



def main():
    parser = argparse.ArgumentParser(description='Yunxiao Flow Pipeline Troubleshooting Tool')
    parser.add_argument('--org-id', required=True, help='Organization ID (24 chars=central org, 32 chars=regional org)')
    parser.add_argument('--pipeline-id', required=True, help='Pipeline ID')
    parser.add_argument('--pipeline-runid', required=True, help='Run ID')
    parser.add_argument('--token', required=False, default=None, help='Personal access token (can also be set via environment variable YUNXIAO_ACCESS_TOKEN)')
    parser.add_argument('--domain', required=False, default=None, help='API domain (auto-inferred from org-id if not provided: 24 chars→openapi-rdc.aliyuncs.com; 32 chars must be explicitly specified)')
    
    args = parser.parse_args()
    
    # Get token: prioritize command line argument, then environment variable
    if not args.token:
        args.token = os.environ.get('YUNXIAO_ACCESS_TOKEN')
    if not args.token:
        parser.error('Must provide --token argument or set environment variable YUNXIAO_ACCESS_TOKEN')
    
    # Auto-infer domain based on org-id length
    if not args.domain:
        if len(args.org_id) == 24:
            args.domain = 'openapi-rdc.aliyuncs.com'
        elif len(args.org_id) == 32:
            parser.error('Regional org (32-char org-id) must explicitly specify API domain via --domain')
        else:
            parser.error(f'Cannot infer domain from org-id length ({len(args.org_id)} chars), please specify --domain explicitly')
    
    print(f"🔍 Fetching pipeline {args.pipeline_id} details... (token: {mask_token(args.token)})\n")
    data = get_pipeline_runs(args.org_id, args.pipeline_id, args.pipeline_runid, args.token, args.domain)
    data['org_id'] = args.org_id
    data['domain'] = args.domain
    pipeline_runs = get_new_flow_info(data, args.token)
    print(f"Retrieved pipeline {args.pipeline_id} run #{args.pipeline_runid} information:")
    # print(pipeline_runs)
    print(json.dumps(pipeline_runs, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    exit(main())
