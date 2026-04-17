# Verification Method: Build AI Animation Story Creation App

## Step-by-Step Verification

### 1. Verify OSS Bucket Created

```bash
aliyun oss stat oss://<OSS_BUCKET_NAME> --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```
**Expected:** Returns Bucket details (Name, Location, CreationDate, etc.)

### 2. Verify Project Created

```bash
aliyun devs list-environments --project-name <ProjectName> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```
**Expected:** Returns environment list containing at least one `production` environment

### 3. Verify Deployment Complete

```bash
aliyun devs get-environment --project-name <ProjectName> --name production --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```
**Expected:** `status.servicesInstances.comfyui.latestDeployment.phase` and `status.servicesInstances.web.latestDeployment.phase` are both `"Finished"`

### 4. Verify Custom Domain Created

```bash
aliyun fc get-custom-domain --domain-name <ProjectName>-web.fcv3.<UID>.cn-hangzhou.fc.devsapp.net --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```
**Expected:** Returns domain details with routeConfig containing `<ProjectName>-web` function route

### 5. Verify Application Accessible

```bash
curl -s --connect-timeout 10 --max-time 30 -o /dev/null -w "%{http_code}" http://<ProjectName>-web.fcv3.<UID>.cn-hangzhou.fc.devsapp.net/
```
**Expected:** HTTP 200
