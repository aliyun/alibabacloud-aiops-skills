#!/bin/bash
# Per-resource deep AWS discovery — run after aws-scan-region.sh
#
# aws-scan-region.sh only runs single list/describe calls (one API call per service).
# This script loops over every main resource and fetches its details:
#
#   EventBridge  — list-rules + list-targets-by-rule on every event bus
#   S3           — get-bucket-lifecycle-configuration + get-bucket-policy per bucket
#   SNS          — list-subscriptions-by-topic per topic
#   IAM          — list-role-policies + get-role-policy per role (inline policies)
#   Lambda       — get-policy per function (resource-based / invoke permissions)
#   API Gateway  — get-resources (embed methods) + get-stages per REST API
#   API GW v2    — get-routes + get-stages per HTTP API
#   ECS          — list-services + describe-services per cluster
#   EKS          — describe-cluster per cluster (version, VPC, addons)
#   ELB v2       — describe-listeners + describe-target-groups per LB
#   Route53      — list-resource-record-sets per hosted zone
#   CloudFront   — get-distribution-config per distribution
#   DynamoDB     — describe-table per table (capacity, GSI/LSI, streams)
#   SQS          — get-queue-attributes per queue (DLQ, policy, encryption)
#   RDS          — describe-db-subnet-groups + describe-db-parameter-groups
#   Step Functions — describe-state-machine per machine
#   ElastiCache  — describe-replication-groups + describe-cache-parameters (user-modified)
#   MSK (Kafka)  — describe-cluster per cluster (broker config, version)
#   Cognito      — describe-user-pool + list-user-pool-clients per pool
#   EFS          — describe-mount-targets + describe-access-points per file system
#
# All sections run in parallel (background subshells), each with a timeout guard.
#
# Usage:
#   ./aws-scan-enrich.sh <region> [path-to-existing-aws-scan-output-dir]
#
# If the optional directory is given and exists, writes:
#   <that-dir>/inventory-deep.md
# Otherwise creates:
#   ./aws-scan-<region>-deep-<timestamp>/inventory-deep.md
#
# Environment (same semantics as aws-scan-region.sh):
#   AWS_SCAN_CMD_TIMEOUT   default 120
#   AWS_SCAN_REDACT        default 1
#   AWS_SCAN_MAX_PARALLEL  default 20
#   AWS_MAX_ATTEMPTS / AWS_RETRY_MODE
#   AWS_SCAN_SECTION_TIMEOUT  Per-section overall timeout (default: 300)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_scan-common.sh
source "$SCRIPT_DIR/_scan-common.sh"

START_TIME=$(date +%s)

AWS_SCAN_SECTION_TIMEOUT="${AWS_SCAN_SECTION_TIMEOUT:-300}"

REGION="${1:?usage: $0 <region> [existing-scan-output-dir]}"
OPTIONAL_DIR="${2:-}"

validate_aws_region "$REGION"

if [[ -n "$OPTIONAL_DIR" ]] && [[ -d "$OPTIONAL_DIR" ]]; then
    DEEP_DIR="$(cd "$OPTIONAL_DIR" && pwd)"
else
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    DEEP_DIR="$(pwd)/aws-scan-${REGION}-deep-${TIMESTAMP}"
    mkdir -p "$DEEP_DIR"
fi
JOBS_DIR="${DEEP_DIR}/.deep-jobs"
OUTPUT_FILE="${DEEP_DIR}/inventory-deep.md"
mkdir -p "$JOBS_DIR"

echo "Deep scan region: $REGION"
echo "Output: $OUTPUT_FILE"
echo "Max parallel: $AWS_SCAN_MAX_PARALLEL  Section timeout: ${AWS_SCAN_SECTION_TIMEOUT}s"
echo ""

# ── helpers ───────────────────────────────────────────────────────────────────
# deep_section <name> <commands...>  — same parallel pattern as aws-scan-region.sh
deep_section() {
    local name="$1"
    shift
    local safe
    safe="$(echo "$name" | tr ' /' '__')"
    local out="$JOBS_DIR/${safe}.txt"
    _wait_for_slot
    {
        echo "## $name"
        echo '```'
        if ! _run_scan_cmd env AWS_DEFAULT_REGION="$REGION" "$@" 2>/dev/null; then
            echo "(no resources, no access, or timeout)"
        fi
        echo '```'
        echo ""
    } > "$out" &
}

# _run_section_with_timeout <output_file> <script> — wraps bash -c with overall timeout
_run_section_with_timeout() {
    local out="$1" script="$2"
    export AWS_SCAN_SECTION_TIMEOUT
    if command -v timeout >/dev/null 2>&1; then
        timeout --signal=TERM "$AWS_SCAN_SECTION_TIMEOUT" bash -c "$script" > "$out" 2>&1 || {
            if [[ ! -s "$out" ]]; then
                printf '## (section timed out)\n```\n(timed out after %ss)\n```\n\n' "$AWS_SCAN_SECTION_TIMEOUT" > "$out"
            fi
        }
    elif command -v perl >/dev/null 2>&1; then
        perl -e 'alarm $ENV{AWS_SCAN_SECTION_TIMEOUT}; exec "bash", "-c", $ARGV[0]' -- "$script" > "$out" 2>&1 || {
            if [[ ! -s "$out" ]]; then
                printf '## (section timed out)\n```\n(timed out after %ss)\n```\n\n' "$AWS_SCAN_SECTION_TIMEOUT" > "$out"
            fi
        }
    else
        bash -c "$script" > "$out" 2>&1
    fi
}

# ── EventBridge: rules + targets on every event bus (single list-rules call) ──
_wait_for_slot
(
    _out="$JOBS_DIR/EventBridge_Rules_and_Targets.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## EventBridge Rules and Targets (all event buses)"
echo "\`\`\`"
aws events list-event-buses --region "$REGION" \
    --query "EventBuses[].Name" --output text 2>/dev/null \
| tr "\t" "\n" | sed "/^$/d" | while read -r bus; do
    echo "=== Event bus: $bus ==="
    # Single JSON call: display rules and extract names for target lookup
    rules_json=$(_run_scan_cmd aws events list-rules --region "$REGION" \
        --event-bus-name "$bus" --output json 2>/dev/null) || continue
    echo "$rules_json" | python3 -c "
import json, sys
rules = json.load(sys.stdin).get(\"Rules\", [])
for r in rules:
    print(f\"  Rule: {r[\"Name\"]}  State: {r.get(\"State\",\"?\")}  Schedule: {r.get(\"ScheduleExpression\",\"-\")}  Pattern: {str(r.get(\"EventPattern\",\"-\"))[:80]}\")
" 2>/dev/null || echo "$rules_json"
    # Extract rule names from the same JSON
    echo "$rules_json" | python3 -c "
import json, sys
for r in json.load(sys.stdin).get(\"Rules\", []):
    print(r[\"Name\"])
" 2>/dev/null | while read -r rule; do
        [ -z "$rule" ] && continue
        echo "--- Targets: $bus / $rule ---"
        _run_scan_cmd aws events list-targets-by-rule --region "$REGION" \
            --event-bus-name "$bus" --rule "$rule" \
            --query "Targets[].[Id,Arn,Input,InputPath]" --output table 2>/dev/null || true
    done
done
echo "\`\`\`"
echo ""
'
) &

# ── S3: lifecycle + bucket policy per bucket ─────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/S3_Bucket_Config.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## S3 Bucket Config (Lifecycle + Policy)"
echo "\`\`\`"
aws s3api list-buckets --query "Buckets[].Name" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r bucket; do
    [ -z "$bucket" ] && continue
    echo "=== $bucket ==="
    echo "-- Lifecycle Rules --"
    _run_scan_cmd aws s3api get-bucket-lifecycle-configuration --bucket "$bucket" \
        --query "Rules[].[ID,Status,Filter,Expiration,Transitions]" \
        --output json 2>/dev/null || echo "(no lifecycle rules)"
    echo "-- Bucket Policy --"
    _run_scan_cmd aws s3api get-bucket-policy --bucket "$bucket" \
        --query "Policy" --output text 2>/dev/null \
    | python3 -c "import sys,json; p=json.load(sys.stdin); [print(\"  Sid:\",s.get(\"Sid\"),\"Effect:\",s.get(\"Effect\"),\"Action:\",s.get(\"Action\"),\"Principal:\",s.get(\"Principal\")) for s in p.get(\"Statement\",[])]" \
        2>/dev/null || echo "(no bucket policy)"
done
echo "\`\`\`"
echo ""
'
) &

# ── SNS: subscriptions per topic ─────────────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/SNS_Subscriptions.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## SNS Subscriptions"
echo "\`\`\`"
aws sns list-topics --region "$REGION" \
    --query "Topics[].TopicArn" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r arn; do
    [ -z "$arn" ] && continue
    echo "--- $arn ---"
    _run_scan_cmd aws sns list-subscriptions-by-topic --topic-arn "$arn" --region "$REGION" \
        --query "Subscriptions[].[Protocol,Endpoint,SubscriptionArn]" \
        --output table 2>/dev/null || true
done
echo "\`\`\`"
echo ""
'
) &

# ── IAM: inline policies per role ────────────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/IAM_Inline_Policies.txt"
    _run_section_with_timeout "$_out" '
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## IAM Inline Policies per Role"
echo "\`\`\`"
aws iam list-roles --no-paginate \
    --query "Roles[].RoleName" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r role; do
    [ -z "$role" ] && continue
    policies=$(aws iam list-role-policies --role-name "$role" \
        --query "PolicyNames" --output text 2>/dev/null)
    [ -z "$policies" ] && continue
    echo "=== $role: $policies ==="
    for p in $policies; do
        _run_scan_cmd aws iam get-role-policy --role-name "$role" --policy-name "$p" \
            --query "PolicyDocument.Statement[].[Effect,Action,Resource]" \
            --output table 2>/dev/null || true
    done
done
echo "\`\`\`"
echo ""
'
) &

# ── Lambda: resource-based policies (invoke permissions) ─────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/Lambda_Resource_Policies.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## Lambda Resource-based Policies"
echo "\`\`\`"
aws lambda list-functions --region "$REGION" \
    --query "Functions[].FunctionName" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r fn; do
    [ -z "$fn" ] && continue
    policy=$(aws lambda get-policy --function-name "$fn" \
        --region "$REGION" --query "Policy" --output text 2>/dev/null) || continue
    echo "--- $fn ---"
    echo "$policy" | python3 -c "
import sys, json
p = json.load(sys.stdin)
for s in p[\"Statement\"]:
    print(\"  Sid:\", s.get(\"Sid\"), \"| Principal:\", s.get(\"Principal\"), \"| Action:\", s.get(\"Action\"))
" 2>/dev/null || echo "$policy"
done
echo "\`\`\`"
echo ""
'
) &

# ── API Gateway REST: get-resources + get-stages per API ─────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/APIGateway_REST_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## API Gateway REST — Resources and Stages per API"
echo "\`\`\`"
aws apigateway get-rest-apis --region "$REGION" \
    --query "items[].id" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r api_id; do
    [ -z "$api_id" ] && continue
    echo "=== API $api_id — get-resources ==="
    _run_scan_cmd aws apigateway get-resources --rest-api-id "$api_id" --region "$REGION" \
        --embed "methods" --output json 2>/dev/null || echo "(no access or timeout)"
    echo "=== API $api_id — get-stages ==="
    _run_scan_cmd aws apigateway get-stages --rest-api-id "$api_id" --region "$REGION" \
        --output table 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── API Gateway v2 (HTTP APIs): routes + stages per API ──────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/APIGateway_HTTP_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## API Gateway v2 (HTTP) — Routes and Stages per API"
echo "\`\`\`"
aws apigatewayv2 get-apis --region "$REGION" \
    --query "Items[].ApiId" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r api_id; do
    [ -z "$api_id" ] && continue
    echo "=== HTTP API $api_id — routes ==="
    _run_scan_cmd aws apigatewayv2 get-routes --api-id "$api_id" --region "$REGION" \
        --query "Items[].[RouteKey,Target,AuthorizationType]" \
        --output table 2>/dev/null || echo "(no access or timeout)"
    echo "=== HTTP API $api_id — stages ==="
    _run_scan_cmd aws apigatewayv2 get-stages --api-id "$api_id" --region "$REGION" \
        --query "Items[].[StageName,AutoDeploy,LastUpdatedDate]" \
        --output table 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── ECS: services + task definitions per cluster ─────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/ECS_Services_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## ECS Services and Tasks per Cluster"
echo "\`\`\`"
aws ecs list-clusters --region "$REGION" \
    --query "clusterArns" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r cluster_arn; do
    [ -z "$cluster_arn" ] && continue
    echo "=== Cluster: $cluster_arn ==="
    services=$(_run_scan_cmd aws ecs list-services --region "$REGION" \
        --cluster "$cluster_arn" --query "serviceArns" --output text 2>/dev/null) || continue
    [ -z "$services" ] && { echo "(no services)"; continue; }
    # describe-services accepts up to 10 at a time
    echo "$services" | tr "\t" "\n" | while read -r svc; do
        [ -z "$svc" ] && continue
        _run_scan_cmd aws ecs describe-services --region "$REGION" \
            --cluster "$cluster_arn" --services "$svc" \
            --query "services[].[serviceName,status,launchType,desiredCount,runningCount,taskDefinition]" \
            --output table 2>/dev/null || true
    done
done
echo "\`\`\`"
echo ""
'
) &

# ── EKS: describe-cluster + addons per cluster ──────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/EKS_Cluster_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## EKS Cluster Details and Addons"
echo "\`\`\`"
aws eks list-clusters --region "$REGION" \
    --query "clusters" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r cluster; do
    [ -z "$cluster" ] && continue
    echo "=== Cluster: $cluster ==="
    _run_scan_cmd aws eks describe-cluster --region "$REGION" --name "$cluster" \
        --query "cluster.[name,version,platformVersion,status,resourcesVpcConfig.[vpcId,subnetIds,securityGroupIds,endpointPublicAccess,endpointPrivateAccess],logging.clusterLogging]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
    echo "--- Addons ---"
    _run_scan_cmd aws eks list-addons --region "$REGION" --cluster-name "$cluster" \
        --query "addons" --output table 2>/dev/null || echo "(no addons)"
done
echo "\`\`\`"
echo ""
'
) &

# ── ELB v2: listeners + target groups per load balancer ──────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/ELBv2_Listeners_Targets.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## ELB v2 — Listeners and Target Groups per LB"
echo "\`\`\`"
aws elbv2 describe-load-balancers --region "$REGION" \
    --query "LoadBalancers[].LoadBalancerArn" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r lb_arn; do
    [ -z "$lb_arn" ] && continue
    echo "=== LB: $lb_arn ==="
    echo "--- Listeners ---"
    _run_scan_cmd aws elbv2 describe-listeners --region "$REGION" \
        --load-balancer-arn "$lb_arn" \
        --query "Listeners[].[Port,Protocol,DefaultActions[0].Type,DefaultActions[0].TargetGroupArn]" \
        --output table 2>/dev/null || echo "(no listeners)"
done
echo "--- All Target Groups ---"
_run_scan_cmd aws elbv2 describe-target-groups --region "$REGION" \
    --query "TargetGroups[].[TargetGroupName,Protocol,Port,TargetType,HealthCheckPath,VpcId]" \
    --output table 2>/dev/null || echo "(no target groups)"
echo "\`\`\`"
echo ""
'
) &

# ── Route53: record sets per hosted zone ─────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/Route53_Records.txt"
    _run_section_with_timeout "$_out" '
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## Route53 Record Sets per Hosted Zone"
echo "\`\`\`"
aws route53 list-hosted-zones \
    --query "HostedZones[].[Id,Name]" --output text 2>/dev/null \
| while read -r zone_id zone_name; do
    [ -z "$zone_id" ] && continue
    echo "=== Zone: $zone_name ($zone_id) ==="
    _run_scan_cmd aws route53 list-resource-record-sets --hosted-zone-id "$zone_id" \
        --query "ResourceRecordSets[].[Name,Type,TTL,AliasTarget.DNSName,ResourceRecords[0].Value]" \
        --output table 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── CloudFront: distribution config per distribution ─────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/CloudFront_Config.txt"
    _run_section_with_timeout "$_out" '
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## CloudFront Distribution Config"
echo "\`\`\`"
aws cloudfront list-distributions \
    --query "DistributionList.Items[].Id" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r dist_id; do
    [ -z "$dist_id" ] && continue
    echo "=== Distribution: $dist_id ==="
    _run_scan_cmd aws cloudfront get-distribution --id "$dist_id" \
        --query "Distribution.DistributionConfig.[Origins.Items[*].[Id,DomainName,S3OriginConfig,CustomOriginConfig],DefaultCacheBehavior.[ViewerProtocolPolicy,AllowedMethods.Items,CachePolicyId,OriginRequestPolicyId],ViewerCertificate.[ACMCertificateArn,SSLSupportMethod,MinimumProtocolVersion],WebACLId]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── DynamoDB: describe-table per table ───────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/DynamoDB_Table_Details.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## DynamoDB Table Details"
echo "\`\`\`"
aws dynamodb list-tables --region "$REGION" \
    --query "TableNames" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r table; do
    [ -z "$table" ] && continue
    echo "=== Table: $table ==="
    _run_scan_cmd aws dynamodb describe-table --region "$REGION" --table-name "$table" \
        --query "Table.[TableName,TableStatus,BillingModeSummary.BillingMode,ProvisionedThroughput.[ReadCapacityUnits,WriteCapacityUnits],GlobalSecondaryIndexes[*].[IndexName,KeySchema,Projection.ProjectionType,ProvisionedThroughput],LocalSecondaryIndexes[*].[IndexName,KeySchema],StreamSpecification,SSEDescription.Status,TableSizeBytes,ItemCount]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── SQS: queue attributes per queue ──────────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/SQS_Queue_Attributes.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## SQS Queue Attributes"
echo "\`\`\`"
aws sqs list-queues --region "$REGION" \
    --query "QueueUrls" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r queue_url; do
    [ -z "$queue_url" ] && continue
    echo "=== $(basename "$queue_url") ==="
    _run_scan_cmd aws sqs get-queue-attributes --region "$REGION" \
        --queue-url "$queue_url" --attribute-names All \
        --query "Attributes.[QueueArn,VisibilityTimeout,MessageRetentionPeriod,DelaySeconds,RedrivePolicy,KmsMasterKeyId,FifoQueue,ContentBasedDeduplication]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── RDS: subnet groups + parameter groups ────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/RDS_Config_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## RDS Subnet Groups and Parameter Groups"
echo "\`\`\`"
echo "--- DB Subnet Groups ---"
_run_scan_cmd aws rds describe-db-subnet-groups --region "$REGION" \
    --query "DBSubnetGroups[].[DBSubnetGroupName,VpcId,DBSubnetGroupDescription,Subnets[*].[SubnetIdentifier,SubnetAvailabilityZone.Name]]" \
    --output json 2>/dev/null || echo "(no subnet groups)"
echo "--- DB Parameter Groups (non-default) ---"
aws rds describe-db-instances --region "$REGION" \
    --query "DBInstances[].[DBInstanceIdentifier,DBParameterGroups[0].DBParameterGroupName]" \
    --output text 2>/dev/null \
| while read -r inst pg; do
    [ -z "$pg" ] && continue
    echo "=== $inst → $pg ==="
    _run_scan_cmd aws rds describe-db-parameters --region "$REGION" \
        --db-parameter-group-name "$pg" \
        --query "Parameters[?Source==\`user\`].[ParameterName,ParameterValue,ApplyType]" \
        --output table 2>/dev/null || true
done
echo "\`\`\`"
echo ""
'
) &

# ── Step Functions: state machine definitions ────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/StepFunctions_Definitions.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## Step Functions State Machine Definitions"
echo "\`\`\`"
aws stepfunctions list-state-machines --region "$REGION" \
    --query "stateMachines[].stateMachineArn" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r sm_arn; do
    [ -z "$sm_arn" ] && continue
    echo "=== $(basename "$sm_arn") ==="
    _run_scan_cmd aws stepfunctions describe-state-machine --region "$REGION" \
        --state-machine-arn "$sm_arn" \
        --query "[name,status,type,loggingConfiguration,definition]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── ElastiCache: replication groups + user-modified parameters ────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/ElastiCache_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## ElastiCache Replication Groups and Parameters"
echo "\`\`\`"
echo "--- Replication Groups ---"
_run_scan_cmd aws elasticache describe-replication-groups --region "$REGION" \
    --query "ReplicationGroups[].[ReplicationGroupId,Description,Status,NodeGroups[0].NodeGroupMembers[0].CacheNodeId,CacheNodeType,SnapshotRetentionLimit,AutomaticFailover,TransitEncryptionEnabled,AtRestEncryptionEnabled]" \
    --output table 2>/dev/null || echo "(no replication groups)"
echo "--- User-Modified Cache Parameters ---"
aws elasticache describe-cache-clusters --region "$REGION" \
    --query "CacheClusters[].[CacheClusterId,CacheParameterGroup.CacheParameterGroupName]" \
    --output text 2>/dev/null \
| while read -r cluster pg; do
    [ -z "$pg" ] && continue
    # Only show user-modified parameters (source=user)
    params=$(_run_scan_cmd aws elasticache describe-cache-parameters --region "$REGION" \
        --cache-parameter-group-name "$pg" \
        --query "Parameters[?Source==\`user\`].[ParameterName,ParameterValue]" \
        --output text 2>/dev/null)
    [ -z "$params" ] && continue
    echo "=== $cluster → $pg ==="
    echo "$params"
done
echo "\`\`\`"
echo ""
'
) &

# ── MSK (Kafka): cluster details ─────────────────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/MSK_Cluster_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## MSK (Kafka) Cluster Details"
echo "\`\`\`"
aws kafka list-clusters --region "$REGION" \
    --query "ClusterInfoList[].ClusterArn" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r cluster_arn; do
    [ -z "$cluster_arn" ] && continue
    echo "=== $(basename "$cluster_arn") ==="
    _run_scan_cmd aws kafka describe-cluster --region "$REGION" \
        --cluster-arn "$cluster_arn" \
        --query "ClusterInfo.[ClusterName,State,CurrentBrokerSoftwareInfo.KafkaVersion,NumberOfBrokerNodes,BrokerNodeGroupInfo.[InstanceType,ClientSubnets,StorageInfo],EncryptionInfo,EnhancedMonitoring]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
done
echo "\`\`\`"
echo ""
'
) &

# ── Cognito: user pool config + app clients ──────────────────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/Cognito_UserPool_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## Cognito User Pool Details"
echo "\`\`\`"
aws cognito-idp list-user-pools --region "$REGION" --max-results 60 \
    --query "UserPools[].Id" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r pool_id; do
    [ -z "$pool_id" ] && continue
    echo "=== Pool: $pool_id ==="
    _run_scan_cmd aws cognito-idp describe-user-pool --region "$REGION" \
        --user-pool-id "$pool_id" \
        --query "UserPool.[Name,Status,MfaConfiguration,Policies.PasswordPolicy,LambdaConfig,SchemaAttributes[*].[Name,AttributeDataType,Required,Mutable]]" \
        --output json 2>/dev/null || echo "(no access or timeout)"
    echo "--- App Clients ---"
    _run_scan_cmd aws cognito-idp list-user-pool-clients --region "$REGION" \
        --user-pool-id "$pool_id" \
        --query "UserPoolClients[].[ClientId,ClientName]" \
        --output table 2>/dev/null || true
done
echo "\`\`\`"
echo ""
'
) &

# ── EFS: mount targets + access points per file system ───────────────────────
_wait_for_slot
(
    _out="$JOBS_DIR/EFS_Deep.txt"
    _run_section_with_timeout "$_out" '
REGION='"'$REGION'"'
AWS_SCAN_CMD_TIMEOUT='"'$AWS_SCAN_CMD_TIMEOUT'"'
source "'"$SCRIPT_DIR/_scan-common.sh"'"
echo "## EFS Mount Targets and Access Points"
echo "\`\`\`"
aws efs describe-file-systems --region "$REGION" \
    --query "FileSystems[].FileSystemId" --output text 2>/dev/null \
| tr "\t" "\n" | while read -r fs_id; do
    [ -z "$fs_id" ] && continue
    echo "=== FileSystem: $fs_id ==="
    echo "--- Mount Targets ---"
    _run_scan_cmd aws efs describe-mount-targets --region "$REGION" \
        --file-system-id "$fs_id" \
        --query "MountTargets[].[MountTargetId,SubnetId,IpAddress,LifeCycleState,AvailabilityZoneName]" \
        --output table 2>/dev/null || echo "(no mount targets)"
    echo "--- Access Points ---"
    _run_scan_cmd aws efs describe-access-points --region "$REGION" \
        --file-system-id "$fs_id" \
        --query "AccessPoints[].[AccessPointId,Name,RootDirectory.Path,PosixUser,LifeCycleState]" \
        --output table 2>/dev/null || echo "(no access points)"
done
echo "\`\`\`"
echo ""
'
) &

# ── Wait + merge ──────────────────────────────────────────────────────────────
echo "Waiting for all deep scan jobs to complete..."
wait
echo "All deep scans done. Merging results..."

_merge_jobs "$JOBS_DIR" "AWS Deep Inventory — Region: $REGION" "$OUTPUT_FILE"

echo ""
echo "Deep sections scanned:"
grep "^## " "$OUTPUT_FILE" | sed 's/^## /  - /' || true

echo ""
echo "Full deep inventory: $OUTPUT_FILE"
echo "Note: AWS_SCAN_REDACT=${AWS_SCAN_REDACT} (set 0 for raw IDs/IPs in inventory)."
_print_elapsed "$START_TIME"
