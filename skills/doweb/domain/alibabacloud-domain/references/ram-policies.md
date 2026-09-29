# RAM permissions

DomainCLI internally reuses intended parent-resolved standard credentials or selected China-site OAuth temporary credentials. The selected principal still needs permission for the underlying service action. Grant only actions required by the user's chosen command. Never grant product-wide wildcards. `whoami` verifies that principal through read-only STS GetCallerIdentity, not product permissions or resource ownership.

The following list is a permission-planning aid, not an authorization to modify RAM policies. Confirm exact action names against the installed leaf help and the current Alibaba Cloud RAM console when an API returns `Forbidden.RAM`.

## required_permissions

### Domain read actions

- `domain:QueryDomainList`
- `domain:QueryDomainByDomainName`
- `domain:QueryAdvancedDomainList`
- `domain:QueryDomainGroupList`
- `domain:QueryContactInfo`
- `domain:QueryRegistrantProfiles`
- `domain:QueryRegistrantProfileRealNameVerificationInfo`
- `domain:QueryDomainRealNameVerificationInfo`
- `domain:QueryEmailVerification`
- `domain:ListEmailVerification`
- `domain:QueryChangeLogList`
- `domain:QueryTaskList`
- `domain:QueryTaskDetailList`
- `domain:QueryTaskInfoHistory`
- `domain:QueryTaskDetailHistory`
- `domain:PollTaskResult`
- `domain:QueryTransferInList`
- `domain:QueryTransferInByInstanceId`
- `domain:CheckTransferInFeasibility`
- `domain:QueryTransferOutInfo`
- `domain:QueryDnsHost`
- `domain:QueryDSRecord`
- `domain:ListServerLock`
- `domain:QueryServerLock`
- `domain:CheckProcessingServerLockApply`
- `domain:CheckMaxYearOfServerLock`
- `domain:DomainKnowledgeRetrieve`
- `domain:CheckSelectedDomainStatus`

Public availability, reference-price, and WHOIS routes may not require account RAM actions. Do not infer a permission from a public HTTP lookup.

### Domain write and financial actions

- `bssapi:QueryAccountBalance`
- `domain:SaveBatchTaskForCreatingOrderActivate`
- `domain:SaveBatchTaskForCreatingOrderRenew`
- `domain:SaveBatchTaskForCreatingOrderTransfer`
- `domain:SetupDomainAutoRenew`
- `domain:SaveBatchDomainRemark`
- `domain:SaveDomainGroup`
- `domain:DeleteDomainGroup`
- `domain:UpdateDomainToDomainGroup`
- `domain:SaveBatchTaskForTransferProhibitionLock`
- `domain:SaveBatchTaskForUpdateProhibitionLock`
- `domain:SaveSingleTaskForQueryingTransferAuthorizationCode`
- `domain:SaveBatchTaskForApplyQuickTransferOutOpenly`
- `domain:SaveBatchTaskForModifyingDomainDns`
- `domain:SaveBatchTaskForUpdatingContactInfoByRegistrantProfileId`
- `domain:SaveRegistrantProfile`
- `domain:DeleteRegistrantProfile`
- `domain:SetDefaultRegistrantProfile`
- `domain:RegistrantProfileRealNameVerification`
- `domain:VerifyContactField`
- `domain:QueryDomainAdminDivision`
- `domain:SubmitEmailVerification`
- `domain:ResendEmailVerification`
- `domain:DeleteEmailVerification`
- `domain:VerifyEmail`
- `domain:SaveSingleTaskForCreatingDnsHost`
- `domain:SaveSingleTaskForModifyingDnsHost`
- `domain:SaveSingleTaskForDeletingDnsHost`
- `domain:SaveSingleTaskForAddingDSRecord`
- `domain:SaveSingleTaskForModifyingDSRecord`
- `domain:SaveSingleTaskForDeletingDSRecord`
- `domain:SendAuthCode`
- `domain:PublishSelectedDomain`

### Alibaba Cloud DNS actions

- `alidns:DescribeDomainRecords`
- `alidns:DescribeDomainRecordInfo`
- `alidns:DescribeSupportLines`
- `alidns:DescribeRecordLogs`
- `alidns:AddDomainRecord`
- `alidns:UpdateDomainRecord`
- `alidns:DeleteDomainRecord`
- `alidns:SetDomainRecordStatus`

### ICP actions

- `beian:RetrieveBeianKnowledge`
- `beian:QueryBeianOrder`
- `companyreg:QuerySuccessIcpData`

`aliyun domain icp fill` opens an official filing page and does not require an OpenAPI RAM action.

### WebsiteBuild read actions

- `websitebuild:QueryInspirationBalance`
- `websitebuild:ListAppInstances`
- `websitebuild:ListAIStaffChatMessages`
- `websitebuild:GetAppWorkspaceDirectory`
- `websitebuild:GetAppFileContent`
- `websitebuild:GetAppPublishStatus`
- `websitebuild:ListAppPublishHistory`
- `websitebuild:GetAIStaffPreviewUrl`
- `websitebuild:ListAppConversations`
- `websitebuild:GetAppConversation`
- `websitebuild:GetAppConversationLockStatus`
- `websitebuild:ListAppInstanceDomains`
- `websitebuild:DescribeAppDomainDnsRecord`
- `websitebuild:ListAppDomainRedirectRecords`
- `websitebuild:QueryMaterialDirectoryTree`
- `websitebuild:QueryMaterialFileList`
- `websitebuild:QueryMaterialFileDetail`
- `websitebuild:QueryMaterialFileSummaryInfo`
- `websitebuild:ListAppPluginFiles`
- `websitebuild:ListAppPlugins`
- `websitebuild:ListMyAppPlugins`
- `websitebuild:ListMarketplaceAppPlugins`
- `websitebuild:GetAppPlugin`
- `websitebuild:ListAppPluginVersions`
- `websitebuild:CreateAppAssistantAgentSsoLogin`

### WebsiteBuild write actions

- `websitebuild:CreateAppChat`
- `websitebuild:ReconnectAppChat`
- `websitebuild:SaveArticleDraft`
- `websitebuild:SaveImageDraft`
- `websitebuild:SaveVideoDraft`
- `websitebuild:BindAppDomain`
- `websitebuild:DeleteAppDomainRedirect`
- `websitebuild:SetAppDomainCertificate`
- `websitebuild:DeleteAppDomainCertificate`
- `websitebuild:UnbindAppDomain`
- `websitebuild:UpdateAppInstanceDomain`
- `websitebuild:CreateMaterialDirectory`
- `websitebuild:DeleteMaterialDirectory`
- `websitebuild:ExportMaterialFile`
- `websitebuild:ModifyMaterialDirectory`
- `websitebuild:ModifyMaterialFile`
- `websitebuild:ModifyMaterialFileStatus`
- `websitebuild:MoveMaterialDirectory`
- `websitebuild:MoveMaterialFile`
- `websitebuild:UploadMaterialFile`
- `websitebuild:DeleteAppInstance`
- `websitebuild:OfflineAppInstance`
- `websitebuild:OnlineAppInstance`
- `websitebuild:PublishAppInstance`
- `websitebuild:RollbackAppCodeSnapshot`
- `websitebuild:RollbackAppInstancePublish`
- `websitebuild:CreateAppPlugin`
- `websitebuild:DeleteAppPlugin`
- `websitebuild:InstallAppPlugin`
- `websitebuild:RollbackAppPluginVersion`
- `websitebuild:UninstallAppPlugin`
- `websitebuild:UpdateAppPlugin`
- `websitebuild:UploadAppPluginVersion`

When the service returns a different exact action in `AccessDeniedDetail.AuthAction`, treat the service response as current truth and update this reference before claiming complete permission coverage.
