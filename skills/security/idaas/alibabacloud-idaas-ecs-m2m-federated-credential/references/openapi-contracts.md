# OpenAPI Request and Response Contracts

Source: official Alibaba Cloud CLI 3.5.1 plugin request/response help, checked 2026-11-03.
These are API contracts, not account fixtures. No example resource IDs are supplied.
`--region` selects the endpoint for every cloud API command; initialize the Skill user-agent before calling.
Do not infer required inputs from the whole federation workflow when executing a scoped read.
Inputs exported by an earlier response are required only by the dependent call.

## RPC Actions

### sts.GetCallerIdentity
- Product: `sts`; API version: `2015-04-01`; gateway: POP RPC.
- CLI command: `aliyun sts get-caller-identity`.
- Required API inputs: none.
- Optional API inputs: none.
- Response fields: `AccountId`, `Arn`, `IdentityType`, `PrincipalId`, `RequestId`, `RoleId`, `UserId`.

### eiam.ListInstances
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam list-instances`.
- Required API inputs: none.
- Optional API inputs: `CrossRegionReplication` → `--cross-region-replication`; `Edition` → `--edition`; `InstanceIds` → `--instance-ids`; `ManagedServiceCode` → `--managed-service-code`; `PageNumber` → `--page-number`; `PageSize` → `--page-size`; `ServiceManaged` → `--service-managed`; `Status` → `--status`.
- Response fields: `Instances`, `Instances[].CreateTime`, `Instances[].CrossRegionReplication`, `Instances[].CrossRegionReplicationRole`, `Instances[].DefaultEndpoint`, `Instances[].DefaultEndpoint.Endpoint`, `Instances[].DefaultEndpoint.Status`, `Instances[].Description`, `Instances[].InstanceFailoverStatus`, `Instances[].InstanceId`, `Instances[].ManagedServiceCode`, `Instances[].ReplicationConfiguration`, `Instances[].ReplicationConfiguration.BackupInstanceId`, `Instances[].ReplicationConfiguration.BackupInstanceRegionId`, `Instances[].ReplicationConfiguration.PrimaryInstanceId`, `Instances[].ReplicationConfiguration.PrimaryInstanceRegionId`, `Instances[].ReplicationConfiguration.ReplicationCreateTime`, `Instances[].ServiceManaged`, `Instances[].Status`, `RequestId`, `TotalCount`.

### eiam.GetInstance
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam get-instance`.
- Required API inputs: `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `Instance`, `Instance.CreateTime`, `Instance.CrossRegionReplication`, `Instance.CrossRegionReplicationRole`, `Instance.DefaultEndpoint`, `Instance.DefaultEndpoint.Endpoint`, `Instance.DefaultEndpoint.Status`, `Instance.Description`, `Instance.DomainConfig`, `Instance.DomainConfig.DefaultDomain`, `Instance.DomainConfig.InitDomain`, `Instance.DomainConfig.InitDomainAutoRedirectStatus`, `Instance.EgressAddresses`, `Instance.InstanceFailoverStatus`, `Instance.InstanceId`, `Instance.ManagedServiceCode`, `Instance.ReplicationConfiguration`, `Instance.ReplicationConfiguration.BackupInstanceId`, `Instance.ReplicationConfiguration.BackupInstanceRegionId`, `Instance.ReplicationConfiguration.PrimaryInstanceId`, `Instance.ReplicationConfiguration.PrimaryInstanceRegionId`, `Instance.ReplicationConfiguration.ReplicationCreateTime`, `Instance.ServiceManaged`, `Instance.Status`, `RequestId`.

### eiam.CreateFederatedCredentialProvider
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam create-federated-credential-provider`.
- Required API inputs: `FederatedCredentialProviderName` → `--federated-credential-provider-name` (string); `FederatedCredentialProviderType` → `--federated-credential-provider-type` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: `CloudIdPProviderConfig` → `--cloud-idp-provider-config`; `Description` → `--description`; `NetworkAccessEndpointId` → `--network-access-endpoint-id`; `OidcProviderConfig` → `--oidc-provider-config`; `Pkcs7ProviderConfig` → `--pkcs7-provider-config`; `PrivateCaProviderConfig` → `--private-ca-provider-config`.
- Response fields: `FederatedCredentialProviderId`, `RequestId`.

### eiam.GetFederatedCredentialProvider
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam get-federated-credential-provider`.
- Required API inputs: `FederatedCredentialProviderId` → `--federated-credential-provider-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `FederatedCredentialProvider`, `FederatedCredentialProvider.CloudIdPProviderConfig`, `FederatedCredentialProvider.CloudIdPProviderConfig.IdentityProviderId`, `FederatedCredentialProvider.CreateTime`, `FederatedCredentialProvider.Description`, `FederatedCredentialProvider.FederatedCredentialProviderId`, `FederatedCredentialProvider.FederatedCredentialProviderName`, `FederatedCredentialProvider.FederatedCredentialProviderType`, `FederatedCredentialProvider.InstanceId`, `FederatedCredentialProvider.NetworkAccessEndpointId`, `FederatedCredentialProvider.OidcProviderConfig`, `FederatedCredentialProvider.OidcProviderConfig.Audiences`, `FederatedCredentialProvider.OidcProviderConfig.DynamicJwks`, `FederatedCredentialProvider.OidcProviderConfig.Issuer`, `FederatedCredentialProvider.OidcProviderConfig.JwksLastObtainedTime`, `FederatedCredentialProvider.OidcProviderConfig.JwksSource`, `FederatedCredentialProvider.OidcProviderConfig.JwksUri`, `FederatedCredentialProvider.OidcProviderConfig.StaticJwks`, `FederatedCredentialProvider.OidcProviderConfig.TrustCondition`, `FederatedCredentialProvider.Pkcs7ProviderConfig`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates[].CertificateMetadata`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates[].CertificateMetadata.NotAfter`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates[].CertificateMetadata.NotBefore`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates[].Content`, `FederatedCredentialProvider.Pkcs7ProviderConfig.Certificates[].Fingerprint`, `FederatedCredentialProvider.Pkcs7ProviderConfig.CmsVerificationMode`, `FederatedCredentialProvider.Pkcs7ProviderConfig.SignatureEffectiveTime`, `FederatedCredentialProvider.Pkcs7ProviderConfig.SigningTimeValueExpression`, `FederatedCredentialProvider.Pkcs7ProviderConfig.TrustAnchorSource`, `FederatedCredentialProvider.Pkcs7ProviderConfig.TrustCondition`, `FederatedCredentialProvider.PrivateCaProviderConfig`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates[].CertificateMetadata`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates[].CertificateMetadata.NotAfter`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates[].CertificateMetadata.NotBefore`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates[].Content`, `FederatedCredentialProvider.PrivateCaProviderConfig.Certificates[].Fingerprint`, `FederatedCredentialProvider.PrivateCaProviderConfig.TrustAnchorSource`, `FederatedCredentialProvider.PrivateCaProviderConfig.TrustCondition`, `FederatedCredentialProvider.Status`, `FederatedCredentialProvider.UpdateTime`, `RequestId`.

### eiam.ListFederatedCredentialProviders
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam list-federated-credential-providers`.
- Required API inputs: `InstanceId` → `--instance-id` (string).
- Optional API inputs: `FederatedCredentialProviderName` → `--federated-credential-provider-name`; `FederatedCredentialProviderType` → `--federated-credential-provider-type`; `MaxResults` → `--max-results`; `NextToken` → `--next-token`; `PreviousToken` → `--previous-token`.
- Response fields: `FederatedCredentialProviders`, `FederatedCredentialProviders[].CloudIdPProviderConfig`, `FederatedCredentialProviders[].CloudIdPProviderConfig.IdentityProviderId`, `FederatedCredentialProviders[].CreateTime`, `FederatedCredentialProviders[].Description`, `FederatedCredentialProviders[].FederatedCredentialProviderId`, `FederatedCredentialProviders[].FederatedCredentialProviderName`, `FederatedCredentialProviders[].FederatedCredentialProviderType`, `FederatedCredentialProviders[].InstanceId`, `FederatedCredentialProviders[].NetworkAccessEndpointId`, `FederatedCredentialProviders[].OidcProviderConfig`, `FederatedCredentialProviders[].OidcProviderConfig.Audiences`, `FederatedCredentialProviders[].OidcProviderConfig.DynamicJwks`, `FederatedCredentialProviders[].OidcProviderConfig.Issuer`, `FederatedCredentialProviders[].OidcProviderConfig.JwksLastObtainedTime`, `FederatedCredentialProviders[].OidcProviderConfig.JwksSource`, `FederatedCredentialProviders[].OidcProviderConfig.JwksUri`, `FederatedCredentialProviders[].OidcProviderConfig.StaticJwks`, `FederatedCredentialProviders[].OidcProviderConfig.TrustCondition`, `FederatedCredentialProviders[].Pkcs7ProviderConfig`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates[].CertificateMetadata`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates[].CertificateMetadata.NotAfter`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates[].CertificateMetadata.NotBefore`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates[].Content`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.Certificates[].Fingerprint`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.CmsVerificationMode`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.SignatureEffectiveTime`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.SigningTimeValueExpression`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.TrustAnchorSource`, `FederatedCredentialProviders[].Pkcs7ProviderConfig.TrustCondition`, `FederatedCredentialProviders[].PrivateCaProviderConfig`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates[].CertificateMetadata`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates[].CertificateMetadata.NotAfter`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates[].CertificateMetadata.NotBefore`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates[].Content`, `FederatedCredentialProviders[].PrivateCaProviderConfig.Certificates[].Fingerprint`, `FederatedCredentialProviders[].PrivateCaProviderConfig.TrustAnchorSource`, `FederatedCredentialProviders[].PrivateCaProviderConfig.TrustCondition`, `FederatedCredentialProviders[].Status`, `FederatedCredentialProviders[].UpdateTime`, `MaxResults`, `NextToken`, `PreviousToken`, `RequestId`, `TotalCount`.

### eiam.CreateApplication
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam create-application`.
- Required API inputs: `ApplicationName` → `--application-name` (string); `ApplicationSourceType` → `--application-source-type` (string); `InstanceId` → `--instance-id` (string); `SsoType` → `--sso-type` (string).
- Optional API inputs: `ApplicationIdentityType` → `--application-identity-type`; `ApplicationOwner` → `--application-owner`; `ApplicationTemplateId` → `--application-template-id`; `CustomFields` → `--custom-fields`; `Description` → `--description`; `LogoUrl` → `--logo-url`.
- Response fields: `ApplicationId`, `RequestId`.

### eiam.GetApplication
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam get-application`.
- Required API inputs: `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `Application`, `Application.ApiInvokeStatus`, `Application.ApplicationCreationType`, `Application.ApplicationId`, `Application.ApplicationIdentityType`, `Application.ApplicationName`, `Application.ApplicationOwner`, `Application.ApplicationOwner.GroupIds`, `Application.ApplicationOwner.UserIds`, `Application.ApplicationSourceType`, `Application.ApplicationTemplateId`, `Application.ApplicationVisibility`, `Application.AuthorizationType`, `Application.ClientId`, `Application.CreateTime`, `Application.CustomFields`, `Application.CustomFields[].FieldName`, `Application.CustomFields[].FieldValue`, `Application.CustomSubjectStatus`, `Application.Description`, `Application.Features`, `Application.InstanceId`, `Application.LogoUrl`, `Application.M2MClientStatus`, `Application.ManagedServiceCode`, `Application.ResourceServerIdentifier`, `Application.ResourceServerSourceType`, `Application.ResourceServerStatus`, `Application.ServiceManaged`, `Application.SmartConfigCapabilities`, `Application.SsoType`, `Application.Status`, `Application.UpdateTime`, `RequestId`.

### eiam.EnableApplicationM2MClient
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam enable-application-m2m-client`.
- Required API inputs: `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.ListApplications
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam list-applications`.
- Required API inputs: `InstanceId` → `--instance-id` (string).
- Optional API inputs: `ApplicationCreationType` → `--application-creation-type`; `ApplicationIdentityType` → `--application-identity-type`; `ApplicationIds` → `--application-ids`; `ApplicationName` → `--application-name`; `ApplicationTemplateId` → `--application-template-id`; `AuthorizationType` → `--authorization-type`; `CustomFields` → `--custom-fields`; `M2MClientStatus` → `--m2m-client-status`; `ManagedServiceCode` → `--managed-service-code`; `PageNumber` → `--page-number`; `PageSize` → `--page-size`; `ResourceServerStatus` → `--resource-server-status`; `ServiceManaged` → `--service-managed`; `SsoType` → `--sso-type`; `Status` → `--status`.
- Response fields: `Applications`, `Applications[].ApplicationCreationType`, `Applications[].ApplicationId`, `Applications[].ApplicationIdentityType`, `Applications[].ApplicationName`, `Applications[].ApplicationSourceType`, `Applications[].ApplicationTemplateId`, `Applications[].ClientId`, `Applications[].CreateTime`, `Applications[].Description`, `Applications[].Features`, `Applications[].InstanceId`, `Applications[].LogoUrl`, `Applications[].ManagedServiceCode`, `Applications[].ResourceServerIdentifier`, `Applications[].ResourceServerSourceType`, `Applications[].ResourceServerStatus`, `Applications[].ServiceManaged`, `Applications[].SsoType`, `Applications[].Status`, `Applications[].UpdateTime`, `RequestId`, `TotalCount`.

### eiam.CreateApplicationFederatedCredential
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam create-application-federated-credential`.
- Required API inputs: `ApplicationFederatedCredentialName` → `--application-federated-credential-name` (string); `ApplicationFederatedCredentialType` → `--application-federated-credential-type` (string); `ApplicationId` → `--application-id` (string); `FederatedCredentialProviderId` → `--federated-credential-provider-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: `AttributeMappings` → `--attribute-mappings`; `Description` → `--description`; `OidcVerificationConfig` → `--oidc-verification-config`; `Pkcs7VerificationConfig` → `--pkcs7-verification-config`; `VerificationCondition` → `--verification-condition`; `VerificationMode` → `--verification-mode`.
- Response fields: `ApplicationFederatedCredentialId`, `RequestId`.

### eiam.ListApplicationFederatedCredentialsForProvider
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam list-application-federated-credentials-for-provider`.
- Required API inputs: `InstanceId` → `--instance-id` (string).
- Optional API inputs: `FederatedCredentialProviderId` → `--federated-credential-provider-id`; `MaxResults` → `--max-results`; `NextToken` → `--next-token`; `PreviousToken` → `--previous-token`.
- Response fields: `ApplicationFederatedCredentials`, `ApplicationFederatedCredentials[].ApplicationFederatedCredentialId`, `ApplicationFederatedCredentials[].ApplicationFederatedCredentialName`, `ApplicationFederatedCredentials[].ApplicationFederatedCredentialType`, `ApplicationFederatedCredentials[].ApplicationId`, `ApplicationFederatedCredentials[].CreateTime`, `ApplicationFederatedCredentials[].Description`, `ApplicationFederatedCredentials[].FederatedCredentialProviderId`, `ApplicationFederatedCredentials[].InstanceId`, `ApplicationFederatedCredentials[].LastUsedTime`, `ApplicationFederatedCredentials[].OidcVerificationConfig`, `ApplicationFederatedCredentials[].OidcVerificationConfig.AzureVmConfig`, `ApplicationFederatedCredentials[].OidcVerificationConfig.AzureVmConfig.PrincipalId`, `ApplicationFederatedCredentials[].OidcVerificationConfig.AzureVmConfig.ResourceGroupName`, `ApplicationFederatedCredentials[].OidcVerificationConfig.AzureVmConfig.SubscriptionId`, `ApplicationFederatedCredentials[].OidcVerificationConfig.AzureVmConfig.VmNames`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GcpVmConfig`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GcpVmConfig.InstanceIds`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GcpVmConfig.ProjectId`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GcpVmConfig.ServiceAccountId`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GenericConfig`, `ApplicationFederatedCredentials[].OidcVerificationConfig.GenericConfig.Subject`, `ApplicationFederatedCredentials[].OidcVerificationConfig.KubernetesConfig`, `ApplicationFederatedCredentials[].OidcVerificationConfig.KubernetesConfig.Namespace`, `ApplicationFederatedCredentials[].OidcVerificationConfig.KubernetesConfig.PodNamePrefix`, `ApplicationFederatedCredentials[].OidcVerificationConfig.KubernetesConfig.ServiceAccountName`, `ApplicationFederatedCredentials[].OidcVerificationConfig.Profile`, `ApplicationFederatedCredentials[].Pkcs7VerificationConfig`, `ApplicationFederatedCredentials[].Pkcs7VerificationConfig.InstanceIds`, `ApplicationFederatedCredentials[].Status`, `ApplicationFederatedCredentials[].UpdateTime`, `ApplicationFederatedCredentials[].VerificationCondition`, `ApplicationFederatedCredentials[].VerificationMode`, `MaxResults`, `NextToken`, `PreviousToken`, `RequestId`, `TotalCount`.

### eiam.CheckInstanceModuleStatus
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam check-instance-module-status`.
- Required API inputs: `InstanceId` → `--instance-id` (string); `ModuleKey` → `--module-key` (string).
- Optional API inputs: `FeatureKey` → `--feature-key`; `ResourceLabelKey` → `--resource-label-key`; `ResourceLabelValue` → `--resource-label-value`; `SubFeatureKey` → `--sub-feature-key`.
- Response fields: `Module`, `Module.ModuleStatus`, `RequestId`.

### eiam.AuthorizeResourceServerToClient
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam authorize-resource-server-to-client`.
- Required API inputs: `ClientApplicationId` → `--client-application-id` (string); `InstanceId` → `--instance-id` (string); `ResourceServerApplicationId` → `--resource-server-application-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.ListResourceServerScopes
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam list-resource-server-scopes`.
- Required API inputs: `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: `AuthorizationType` → `--authorization-type`; `MaxResults` → `--max-results`; `NextToken` → `--next-token`; `PreviousToken` → `--previous-token`; `ResourceServerScopeIds` → `--resource-server-scope-ids`; `ResourceServerScopeName` → `--resource-server-scope-name`; `ResourceServerScopeType` → `--resource-server-scope-type`; `ResourceServerScopeValue` → `--resource-server-scope-value`.
- Response fields: `MaxResults`, `NextToken`, `PreviousToken`, `RequestId`, `ResourceServerScopes`, `ResourceServerScopes[].ApplicationId`, `ResourceServerScopes[].AuthorizationType`, `ResourceServerScopes[].InstanceId`, `ResourceServerScopes[].ResourceServerScopeId`, `ResourceServerScopes[].ResourceServerScopeName`, `ResourceServerScopes[].ResourceServerScopeType`, `ResourceServerScopes[].ResourceServerScopeValue`, `TotalCount`.

### eiam.AuthorizeResourceServerScopesToClient
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam authorize-resource-server-scopes-to-client`.
- Required API inputs: `ClientApplicationId` → `--client-application-id` (string); `InstanceId` → `--instance-id` (string); `ResourceServerApplicationId` → `--resource-server-application-id` (string); `ResourceServerScopeIds` → `--resource-server-scope-ids` (array).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DisableApplicationFederatedCredential
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam disable-application-federated-credential`.
- Required API inputs: `ApplicationFederatedCredentialId` → `--application-federated-credential-id` (string); `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DeleteApplicationFederatedCredential
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam delete-application-federated-credential`.
- Required API inputs: `ApplicationFederatedCredentialId` → `--application-federated-credential-id` (string); `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DisableFederatedCredentialProvider
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam disable-federated-credential-provider`.
- Required API inputs: `FederatedCredentialProviderId` → `--federated-credential-provider-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DeleteFederatedCredentialProvider
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam delete-federated-credential-provider`.
- Required API inputs: `FederatedCredentialProviderId` → `--federated-credential-provider-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DisableApplication
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam disable-application`.
- Required API inputs: `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### eiam.DeleteApplication
- Product: `eiam`; API version: `2021-12-01`; gateway: POP RPC.
- CLI command: `aliyun eiam delete-application`.
- Required API inputs: `ApplicationId` → `--application-id` (string); `InstanceId` → `--instance-id` (string).
- Optional API inputs: none.
- Response fields: `RequestId`.

### ecs.DescribeInstances
- Product: `ecs`; API version: `2014-05-26`; gateway: POP RPC.
- CLI command: `aliyun ecs describe-instances`.
- Required API inputs: `RegionId` → `--biz-region-id` (string).
- Optional API inputs: `AdditionalAttributes` → `--additional-attributes`; `KeyPairName` → `--biz-key-pair-name`; `DeviceAvailable` → `--device-available`; `DryRun` → `--dry-run`; `EipAddresses` → `--eip-addresses`; `Filter.1.Key` → `--filter-1-key`; `Filter.1.Value` → `--filter-1-value`; `Filter.2.Key` → `--filter-2-key`; `Filter.2.Value` → `--filter-2-value`; `Filter.3.Key` → `--filter-3-key`; `Filter.3.Value` → `--filter-3-value`; `Filter.4.Key` → `--filter-4-key`; `Filter.4.Value` → `--filter-4-value`; `HpcClusterId` → `--hpc-cluster-id`; `HttpEndpoint` → `--http-endpoint`; `HttpPutResponseHopLimit` → `--http-put-response-hop-limit`; `HttpTokens` → `--http-tokens`; `ImageId` → `--image-id`; `InnerIpAddresses` → `--inner-ip-addresses`; `InstanceChargeType` → `--instance-charge-type`; `InstanceIds` → `--instance-ids`; `InstanceName` → `--instance-name`; `InstanceNetworkType` → `--instance-network-type`; `InstanceType` → `--instance-type`; `InstanceTypeFamily` → `--instance-type-family`; `InternetChargeType` → `--internet-charge-type`; `IoOptimized` → `--io-optimized`; `Ipv6Address` → `--ipv6-address`; `LockReason` → `--lock-reason`; `MaxResults` → `--max-results`; `NeedSaleCycle` → `--need-sale-cycle`; `NextToken` → `--next-token`; `PageNumber` → `--page-number`; `PageSize` → `--page-size`; `PrivateIpAddresses` → `--private-ip-addresses`; `PublicIpAddresses` → `--public-ip-addresses`; `RdmaIpAddresses` → `--rdma-ip-addresses`; `ResourceGroupId` → `--resource-group-id`; `SecurityGroupId` → `--security-group-id`; `Status` → `--status`; `Tag` → `--tag`; `VpcId` → `--vpc-id`; `VSwitchId` → `--vswitch-id`; `ZoneId` → `--zone-id`.
- Response fields: `Instances`, `Instances[].AdditionalInfo`, `Instances[].AdditionalInfo.EnableHighDensityMode`, `Instances[].AdditionalInfo.ManagedHostId`, `Instances[].AdditionalInfo.NodeSerialNumber`, `Instances[].AutoReleaseTime`, `Instances[].ClockOptions`, `Instances[].ClockOptions.PtpStatus`, `Instances[].ClusterId`, `Instances[].Cpu`, `Instances[].CpuOptions`, `Instances[].CpuOptions.CoreCount`, `Instances[].CpuOptions.EnableVISST`, `Instances[].CpuOptions.EnableVRDT`, `Instances[].CpuOptions.NestedVirtualization`, `Instances[].CpuOptions.Numa`, `Instances[].CpuOptions.ThreadsPerCore`, `Instances[].CpuOptions.TopologyType`, `Instances[].CpuOptions.TurboMode`, `Instances[].CreationTime`, `Instances[].CreditSpecification`, `Instances[].DedicatedHostAttribute`, `Instances[].DedicatedHostAttribute.DedicatedHostClusterId`, `Instances[].DedicatedHostAttribute.DedicatedHostId`, `Instances[].DedicatedHostAttribute.DedicatedHostName`, `Instances[].DedicatedInstanceAttribute`, `Instances[].DedicatedInstanceAttribute.Affinity`, `Instances[].DedicatedInstanceAttribute.Tenancy`, `Instances[].DeletionProtection`, `Instances[].DeploymentSetGroupNo`, `Instances[].DeploymentSetId`, `Instances[].Description`, `Instances[].DeviceAvailable`, `Instances[].EcsCapacityReservationAttr`, `Instances[].EcsCapacityReservationAttr.CapacityReservationId`, `Instances[].EcsCapacityReservationAttr.CapacityReservationPreference`, `Instances[].EipAddress`, `Instances[].EipAddress.AllocationId`, `Instances[].EipAddress.Bandwidth`, `Instances[].EipAddress.InternetChargeType`, `Instances[].EipAddress.IpAddress`, `Instances[].EipAddress.IsSupportUnassociate`, `Instances[].EnableNVS`, `Instances[].ExpiredTime`, `Instances[].GPUAmount`, `Instances[].GPUSpec`, `Instances[].HibernationOptions`, `Instances[].HibernationOptions.Configured`, `Instances[].HostName`, `Instances[].HpcClusterId`, `Instances[].ISP`, `Instances[].ImageId`, `Instances[].ImageOptions`, `Instances[].ImageOptions.CurrentOSNVMeSupported`, `Instances[].ImageOptions.LoginAsNonRoot`, `Instances[].InnerIpAddress`, `Instances[].InstanceChargeType`, `Instances[].InstanceId`, `Instances[].InstanceName`, `Instances[].InstanceNetworkType`, `Instances[].InstanceType`, `Instances[].InstanceTypeFamily`, `Instances[].InternetChargeType`, `Instances[].InternetMaxBandwidthIn`, `Instances[].InternetMaxBandwidthOut`, `Instances[].IoOptimized`, `Instances[].KeyPairName`, `Instances[].LocalStorageAmount`, `Instances[].LocalStorageCapacity`, `Instances[].Memory`, `Instances[].MetadataOptions`, `Instances[].MetadataOptions.HttpEndpoint`, `Instances[].MetadataOptions.HttpPutResponseHopLimit`, `Instances[].MetadataOptions.HttpTokens`, `Instances[].MetadataOptions.InstanceMetadataTags`, `Instances[].NetworkInterfaces`, `Instances[].NetworkInterfaces[].Ipv4PrefixSets`, `Instances[].NetworkInterfaces[].Ipv4PrefixSets[].Ipv4Prefix`, `Instances[].NetworkInterfaces[].Ipv6PrefixSets`, `Instances[].NetworkInterfaces[].Ipv6PrefixSets[].Ipv6Prefix`, `Instances[].NetworkInterfaces[].Ipv6Sets`, `Instances[].NetworkInterfaces[].Ipv6Sets[].Ipv6Address`, `Instances[].NetworkInterfaces[].Ipv6Sets[].Primary`, `Instances[].NetworkInterfaces[].MacAddress`, `Instances[].NetworkInterfaces[].NetworkInterfaceId`, `Instances[].NetworkInterfaces[].PrimaryIpAddress`, `Instances[].NetworkInterfaces[].PrivateIpSets`, `Instances[].NetworkInterfaces[].PrivateIpSets[].Primary`, `Instances[].NetworkInterfaces[].PrivateIpSets[].PrivateDnsName`, `Instances[].NetworkInterfaces[].PrivateIpSets[].PrivateIpAddress`, `Instances[].NetworkInterfaces[].Type`, `Instances[].OSName`, `Instances[].OSNameEn`, `Instances[].OSType`, `Instances[].OperationLocks`, `Instances[].OperationLocks[].LockMsg`, `Instances[].OperationLocks[].LockReason`, `Instances[].PrivateDnsNameOptions`, `Instances[].PrivateDnsNameOptions.EnableInstanceIdDnsAAAARecord`, `Instances[].PrivateDnsNameOptions.EnableInstanceIdDnsARecord`, `Instances[].PrivateDnsNameOptions.EnableIpDnsARecord`, `Instances[].PrivateDnsNameOptions.EnableIpDnsPtrRecord`, `Instances[].PrivateDnsNameOptions.HostnameType`, `Instances[].PublicIpAddress`, `Instances[].RdmaIpAddress`, `Instances[].Recyclable`, `Instances[].RegionId`, `Instances[].ResourceGroupId`, `Instances[].SaleCycle`, `Instances[].SecurityGroupIds`, `Instances[].SecurityOptions`, `Instances[].SecurityOptions.EnableSecureBoot`, `Instances[].SerialNumber`, `Instances[].SpotDuration`, `Instances[].SpotInterruptionBehavior`, `Instances[].SpotPriceLimit`, `Instances[].SpotStrategy`, `Instances[].StartTime`, `Instances[].Status`, `Instances[].StoppedMode`, `Instances[].Tags`, `Instances[].Tags[].TagKey`, `Instances[].Tags[].TagValue`, `Instances[].VlanId`, `Instances[].VpcAttributes`, `Instances[].VpcAttributes.NatIpAddress`, `Instances[].VpcAttributes.PrivateIpAddress`, `Instances[].VpcAttributes.VSwitchId`, `Instances[].VpcAttributes.VpcId`, `Instances[].ZoneId`, `NextToken`, `PageNumber`, `PageSize`, `RequestId`, `TotalCount`.

## Instance OAuth HTTP API

### Instance token endpoint (HTTP)

The independently specified HTTP request and response contract is in
[oauth-token.openapi.yaml](oauth-token.openapi.yaml). It defines all required
form fields and response schemas without a fictitious POP Action.
- This instance API is not a POP RPC Action and must not be registered under a fictitious eiam Action name.
- Endpoint host: the selected real instance endpoint returned by GetInstance.
- Content-Type: `application/x-www-form-urlencoded`.
- Required form fields: `grant_type=client_credentials`, `client_id` (actual M2M application ID), `client_assertion_type=urn:cloud:idaas:params:oauth:client-assertion-type:pkcs7-bearer`, `client_assertion` (the actual ECS PKCS#7 signature), `application_federated_credential_name` (the actual credential name), and `scope` (the requested authorized resource scope).
- The assertion is sensitive: save it in a permission-restricted temporary file, send it without logging its content, then remove that file.
- Success fields: `access_token`, `token_type`, `expires_in`; error fields: `error`, `error_description`.
- A non-JSON HTTP 200 or a WAF challenge does not establish authentication success or an expected OAuth rejection. Report it as an infrastructure failure; do not disable TLS or bypass protection.
