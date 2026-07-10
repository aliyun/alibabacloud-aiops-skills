# Pipeline Runtime Environment and Workspace
Call yunxiao_flow_get_job_step_log.py to get step logs. Based on the log information and knowledge base, further analyze the root cause and provide solutions. Before analyzing, make sure to clarify the following questions:
* What build cluster is the job using
* What build environment is the job using
* Whether the current step has cloned code. Check the "Download Pipeline Source" option in the corresponding job: ["Download All Pipeline Sources", "Do Not Download Pipeline Sources", "Download Partial Pipeline Sources"]
* What branch and commit were used for code cloning

**Note**:
* Build cluster name must NOT be obtained from `params.buildNodeGroup`. It **MUST** be obtained from the "Request Runtime Environment" step logs.
* Job workspace must be obtained from the `PROJECT_DIR` in the Pipeline Cache step


Yunxiao default build clusters are currently only available in three regions: Beijing, Hangzhou, and Hong Kong. Beijing and Hangzhou are in mainland China and cannot directly access overseas repositories. The Hong Kong region can access overseas repositories.
Build cluster sample logs:
```json
[Build Cluster Info]
>> Cluster Name    : Yunxiao China Hong Kong Build Cluster
```
VPC build cluster (managed build cluster), supports Shanghai, Beijing, Shenzhen, Hangzhou, Singapore (ap-southeast-1), sample log:
```json
[Build Cluster Info]
>> Cluster Name    : Hangzhou VPC Build Cluster
```
Private build cluster log:
```json
[Runner Group Info]:
>> RunnerGroupId   : xxxxx
>> RunnerGroupName : xxxxx
```


## Common Issues
### Clean workspace reports error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock, Is the docker daemon running?
This often occurs on private build machines. The cause is that Docker has not been started on the private build machine. You need to run `docker daemon` first.

### Request runtime environment fails with message "canceled"
The container image used for the build environment must have the `root` user and have `jq` installed.

### Execution failed, the current build cluster is a managed cluster, vpcId:xxxxx, vswitchId:xxxxxx, securityGroupId:xxxxx, endpoint:xxxxxxxx. Please check whether the network connectivity between the selected VPC and endpoint is normal
**Note**: In the pipeline basic information, the following additional information needs to be displayed:
* vpcId
* vswitchId
* securityGroupId
* endpoint
* Image address (specifyContainerImageId)
* Whether private image is used (usePrivateSpecifyContainerImage)
* Service connection for private image (privateSpecifyContainerImageServiceConnection)

1. Determine whether it is a central or regional organization based on the `endpoint`:
* `endpoint` is `devops-build-new.aliyuncs.com`:
    * a. Check VPC cluster network connectivity and security group rules. You can create an ECS under the same VPC, VSW, and security group as the `VPC build cluster` and access the `endpoint` to check network connectivity.
    * b. If the image is not from `build-steps-public-registry.cn-beijing.cr.aliyuncs.com`, it means a non-Yunxiao default image is used. You need to check if the image address is accessible and if the private image repository username and password are correct.
* `endpoint` is NOT `devops-build-new.aliyuncs.com`:
    * a. Ensure the VPC has public network access capability, otherwise Yunxiao will not be able to pull build tasks and scheduling instructions.
    * b. Check VPC cluster network connectivity and security group rules. You can create an ECS under the same VPC, VSW, and security group as the `VPC build cluster` and access the `endpoint` to check network connectivity. If you encounter `Could not resolve host`, you need to reconfigure the `vpc` and `vswitch` for the organization.
    * c. If the image is not from `build-steps-public-registry.cn-beijing.cr.aliyuncs.com`, it means a non-Yunxiao default image is used. You need to check if the image address is accessible and if the private image repository username and password are correct.
