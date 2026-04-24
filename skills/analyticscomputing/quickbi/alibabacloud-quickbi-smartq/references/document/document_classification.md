# 文档分类体系 — 详细字段定义（V2.0）

本文件定义了 **10 大分类组、37 个文档子类型**及其标准提取字段。Agent 提取文本字段并进行归并时，必须参照此文件。

**字段命名规则**：英文 `snake_case`，Excel 表头使用中文名（括号内为英文字段名）。每个子类型的字段列表中，`filename`（源文件名）为隐含首列，无需在此定义。

---

## A. 财务与税务类 (finance-tax)

### A1. 增值税发票 (vat-invoice)
*(Sheet: `增值税发票`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| invoice_type | 发票类型 | 专用/普通/电子/红字 |
| invoice_code | 发票代码 | 10-12位 |
| invoice_number | 发票号码 | 8位 |
| date | 开票日期 | YYYY-MM-DD |
| buyer_name | 购买方名称 | |
| buyer_tax_id | 购买方税号 | |
| seller_name | 销售方名称 | |
| seller_tax_id | 销售方税号 | |
| items | 货物/服务名称 | 多项分号分隔 |
| amount_before_tax | 金额（不含税） | 数值，2位小数 |
| tax_rate | 税率 | 如 13%、9%、6% |
| tax_amount | 税额 | 数值 |
| total_amount | 价税合计 | 数值 |
| remarks | 备注 | |

### A2. 银行回单 (bank-receipt)
*(Sheet: `银行回单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| bank_name | 银行名称 | |
| serial_number | 流水号/凭证号 | |
| transaction_date | 交易日期 | YYYY-MM-DD |
| payer_name | 付款人名称 | |
| payer_account | 付款人账号 | |
| payee_name | 收款人名称 | |
| payee_account | 收款人账号 | |
| amount | 交易金额 | 数值 |
| currency | 币种 | 默认 CNY |
| transaction_type | 交易类型 | 转账/汇款/代付等 |
| purpose | 用途/摘要 | |

### A3. 银行对账单 (bank-statement)
*(Sheet: `银行对账单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| bank_name | 银行名称 | |
| account_number | 账号 | |
| account_name | 户名 | |
| statement_period | 对账周期 | 如 2026-01 至 2026-03 |
| opening_balance | 期初余额 | 数值 |
| closing_balance | 期末余额 | 数值 |
| total_debit | 借方合计 | 数值 |
| total_credit | 贷方合计 | 数值 |
| transaction_count | 交易笔数 | 整数 |

### A4. 费用报销单 (expense-claim)
*(Sheet: `费用报销单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| applicant | 报销人 | |
| department | 部门 | |
| claim_date | 报销日期 | YYYY-MM-DD |
| expense_items | 费用项目 | 分号分隔 |
| total_amount | 报销金额 | 数值 |
| payment_method | 支付方式 | 现金/转账等 |
| approver | 审批人 | |
| remarks | 备注 | |

### A5. 合同/协议 (contract)
*(Sheet: `合同协议`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| contract_number | 合同编号 | |
| contract_title | 合同名称 | |
| party_a | 甲方 | |
| party_b | 乙方 | |
| contract_type | 合同类型 | 采购/服务/租赁/其他 |
| effective_date | 生效日期 | YYYY-MM-DD |
| expiry_date | 到期日期 | YYYY-MM-DD |
| contract_value | 合同金额 | 数值 |
| currency | 币种 | 默认 CNY |
| key_terms | 关键条款 | 摘要≤150字 |
| signature_date | 签署日期 | YYYY-MM-DD |

### A6. 税务申报表 (tax-return)
*(Sheet: `税务申报表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| taxpayer_name | 纳税人名称 | |
| tax_id | 纳税人识别号 | |
| declaration_period | 申报所属期 | YYYY-MM |
| tax_type | 税种 | 增值税/企业所得税等 |
| taxable_amount | 计税依据 | 数值 |
| tax_payable | 应纳税额 | 数值 |
| tax_paid | 已缴税额 | 数值 |
| deduction_amount | 减免税额 | 数值 |
| declaration_status | 申报状态 | 已申报/未申报/更正 |

### A7. 财务报表 (financial-statement)
*(Sheet: `财务报表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| company_name | 企业名称 | |
| report_period | 报表期间 | 如 2025-Q3 |
| total_assets | 资产总额 | 数值 |
| total_liabilities | 负债总额 | 数值 |
| equity | 所有者权益 | 数值 |
| revenue | 营业收入 | 数值 |
| net_profit | 净利润 | 数值 |
| cash_flow_operating | 经营现金流 | 数值 |
| audit_opinion | 审计意见 | 无保留/保留/否定等 |

### A8. 收据/付款凭证 (receipt-payment)
*(Sheet: `收据付款凭证`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| receipt_number | 收据编号 | |
| date | 收款日期 | YYYY-MM-DD |
| payer | 付款方 | |
| payee | 收款方 | |
| amount | 金额 | 数值 |
| payment_method | 支付方式 | 现金/转账/支票等 |
| purpose | 款项用途 | |
| issuer_signature | 开具人签字 | 文本或“有/无” |

---

## B. 人力资源类 (hr)

### B1. 简历 (resume)
*(Sheet: `简历`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| name | 姓名 | |
| gender | 性别 | |
| birth_date | 出生日期 | YYYY-MM-DD 或年龄 |
| phone | 手机号 | |
| email | 邮箱 | |
| highest_education | 最高学历 | 本科/硕士/博士等 |
| school | 毕业院校 | 最高学历院校 |
| major | 专业 | |
| work_years | 工作年限 | |
| latest_company | 最近工作单位 | |
| latest_position | 最近职位 | |
| skills | 技能关键词 | 用分号分隔 |
| expected_salary | 期望薪资 | 如有 |

### B2. 劳动合同 (labor-contract)
*(Sheet: `劳动合同`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| employee_name | 员工姓名 | |
| id_number | 身份证号 | |
| employer_name | 用人单位 | |
| contract_type | 合同类型 | 固定期限/无固定期限/完成一定工作 |
| start_date | 合同起始日 | YYYY-MM-DD |
| end_date | 合同终止日 | YYYY-MM-DD |
| position | 岗位 | |
| work_location | 工作地点 | |
| salary | 薪酬 | 数值或描述 |
| probation_period | 试用期 | 如 3个月 |
| probation_salary | 试用期薪酬 | |
| signature_date | 签订日期 | YYYY-MM-DD |

### B3. 离职证明 (resignation-cert)
*(Sheet: `离职证明`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| employee_name | 员工姓名 | |
| id_number | 身份证号 | |
| company_name | 公司名称 | |
| position | 职位 | |
| entry_date | 入职日期 | YYYY-MM-DD |
| leave_date | 离职日期 | YYYY-MM-DD |
| leave_reason | 离职原因 | 如有 |
| issue_date | 开具日期 | YYYY-MM-DD |

### B4. 工资条 (payslip)
*(Sheet: `工资条`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| employee_name | 员工姓名 | |
| employee_id | 工号 | |
| pay_period | 工资周期 | 如 2026-03 |
| base_salary | 基本工资 | 数值 |
| allowances | 津贴/补贴 | 数值 |
| overtime_pay | 加班费 | 数值 |
| bonus | 奖金 | 数值 |
| gross_pay | 应发合计 | 数值 |
| social_insurance | 社保扣除 | 数值 |
| housing_fund | 公积金扣除 | 数值 |
| tax | 个税扣除 | 数值 |
| other_deductions | 其他扣款 | 数值 |
| net_pay | 实发工资 | 数值 |

### B5. 考勤记录 (attendance-record)
*(Sheet: `考勤记录`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| employee_id | 员工ID | |
| date | 日期 | YYYY-MM-DD |
| clock_in | 打卡时间(入) | HH:MM |
| clock_out | 打卡时间(出) | HH:MM |
| work_hours | 工时 | 数值 |
| status | 异常状态 | 正常/迟到/早退/缺卡/请假 |
| department | 部门 | |

### B6. 培训证书 (training-cert)
*(Sheet: `培训证书`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| trainee_name | 学员姓名 | |
| course_name | 课程名称 | |
| training_org | 培训机构 | |
| issue_date | 颁发日期 | YYYY-MM-DD |
| valid_until | 有效期至 | YYYY-MM-DD |
| certificate_no | 证书编号 | |
| credits_hours | 学分/课时 | 数值 |

### B7. 绩效考核表 (performance-review)
*(Sheet: `绩效考核表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| employee_id | 员工ID | |
| review_period | 考核周期 | 如 2025-Q3 |
| kpi_scores | KPI得分 | 指标:得分，分号分隔 |
| overall_rating | 综合评级 | S/A/B/C/D |
| manager_comments | 主管评语 | 摘要 |
| next_goals | 下期目标 | 摘要 |
| review_date | 考核日期 | YYYY-MM-DD |

---

## C. 供应链与采购类 (supply-chain)

### C1. 采购订单 (purchase-order)
*(Sheet: `采购订单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| po_number | 订单编号 | |
| date | 下单日期 | YYYY-MM-DD |
| supplier | 供应商 | |
| buyer | 采购方 | |
| items | 物料/商品 | 多项用分号分隔 |
| quantities | 数量 | 对应 items |
| unit_prices | 单价 | 对应 items |
| total_amount | 总金额 | 数值 |
| currency | 币种 | 默认 CNY |
| delivery_date | 交货日期 | YYYY-MM-DD |
| payment_terms | 付款条件 | |

### C2. 送货单 (delivery-note)
*(Sheet: `送货单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| delivery_number | 送货单号 | |
| date | 送货日期 | YYYY-MM-DD |
| supplier | 供应商/发货方 | |
| receiver | 收货方 | |
| items | 货物名称 | 多项用分号分隔 |
| quantities | 数量 | 对应 items |
| delivery_address | 送货地址 | |
| receiver_name | 签收人 | |
| related_po | 关联采购订单号 | 如有 |

### C3. 入库单 (warehouse-receipt)
*(Sheet: `入库单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| receipt_number | 入库单号 | |
| date | 入库日期 | YYYY-MM-DD |
| supplier | 供应商 | |
| warehouse | 入库仓库 | |
| items | 物料名称 | 多项用分号分隔 |
| quantities | 数量 | 对应 items |
| inspector | 验收人 | |
| related_po | 关联采购订单号 | 如有 |
| remarks | 备注 | |

### C4. 质检报告 (quality-report)
*(Sheet: `质检报告`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| report_number | 报告编号 | |
| date | 检测日期 | YYYY-MM-DD |
| product_name | 产品名称 | |
| batch_number | 批号 | |
| specification | 规格型号 | |
| test_items | 检测项目 | 多项用分号分隔 |
| test_results | 检测结果 | 对应 test_items |
| conclusion | 结论 | 合格/不合格 |
| inspector | 检验员 | |
| issuing_org | 出具机构 | |

### C5. 供应商评估表 (supplier-evaluation)
*(Sheet: `供应商评估表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| supplier_name | 供应商名称 | |
| evaluation_period | 评估周期 | 如 2025-Q3 |
| quality_score | 质量评分 | 1-10分 |
| delivery_score | 交期评分 | 1-10分 |
| cost_score | 价格评分 | 1-10分 |
| service_score | 服务评分 | 1-10分 |
| overall_rating | 综合评级 | A/B/C/D |
| risk_level | 风险等级 | 高/中/低 |
| evaluator | 评估人 | |

### C6. 库存盘点表 (inventory-count)
*(Sheet: `库存盘点表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| warehouse | 仓库名称 | |
| location_code | 库位编码 | |
| item_code | 物料编码 | |
| book_qty | 账面数量 | 数值 |
| actual_qty | 实盘数量 | 数值 |
| variance_qty | 差异数量 | 数值 |
| variance_reason | 差异原因 | 摘要 |
| count_date | 盘点日期 | YYYY-MM-DD |
| counter | 盘点人 | |

---

## D. 行政与法务类 (admin-legal)

### D1. 营业执照 (business-license)
*(Sheet: `营业执照`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| company_name | 企业名称 | |
| unified_credit_code | 统一社会信用代码 | 18位 |
| legal_representative | 法定代表人 | |
| company_type | 企业类型 | 有限责任/股份有限等 |
| registered_capital | 注册资本 | |
| establishment_date | 成立日期 | YYYY-MM-DD |
| business_scope | 经营范围 | 摘要，200字以内 |
| address | 住所 | |
| valid_period | 营业期限 | |

### D2. 身份证 (id-card)
*(Sheet: `身份证`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| name | 姓名 | |
| gender | 性别 | 男/女 |
| ethnicity | 民族 | |
| birth_date | 出生日期 | YYYY-MM-DD |
| address | 住址 | |
| id_number | 身份证号码 | 18位 |
| issuing_authority | 签发机关 | |
| valid_period | 有效期限 | 起止日期 |

### D3. 护照 (passport)
*(Sheet: `护照`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| name_cn | 中文姓名 | |
| name_en | 英文姓名 | |
| nationality | 国籍 | |
| gender | 性别 | |
| birth_date | 出生日期 | YYYY-MM-DD |
| birth_place | 出生地 | |
| passport_number | 护照号码 | |
| issue_date | 签发日期 | YYYY-MM-DD |
| expiry_date | 有效期至 | YYYY-MM-DD |
| issuing_authority | 签发机关 | |

### D4. 保密协议 (nda)
*(Sheet: `保密协议`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| party_a | 甲方 | |
| party_b | 乙方 | |
| sign_date | 签署日期 | YYYY-MM-DD |
| confidential_period | 保密期限 | 如 3年/永久 |
| scope_summary | 保密范围摘要 | ≤150字 |
| penalty_clause | 违约赔偿条款 | 摘要 |
| governing_law | 管辖法律 | |

### D5. 资质证书 (qualification-license)
*(Sheet: `资质证书`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| cert_number | 证书编号 | |
| holder_name | 持证主体 | |
| issuing_authority | 发证机关 | |
| issue_date | 发证日期 | YYYY-MM-DD |
| expiry_date | 有效期至 | YYYY-MM-DD |
| license_scope | 许可范围 | 摘要 |
| status | 状态 | 有效/吊销/过期 |

### D6. 公文/通知 (official-notice)
*(Sheet: `公文通知`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| doc_number | 文号 | |
| issuing_dept | 发文机关 | |
| title | 标题 | |
| publish_date | 发布日期 | YYYY-MM-DD |
| target_audience | 主送/抄送单位 | |
| content_summary | 正文摘要 | ≤200字 |
| urgency | 紧急程度 | 特急/加急/平件 |
| confidential_level | 密级 | 绝密/机密/秘密/公开 |

---

## E. 医疗类 (medical)

### E1. 病历 (medical-record)
*(Sheet: `病历`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| patient_name | 患者姓名 | |
| gender | 性别 | |
| age | 年龄 | |
| visit_date | 就诊日期 | YYYY-MM-DD |
| hospital | 医疗机构 | |
| department | 科室 | |
| doctor | 主治医生 | |
| chief_complaint | 主诉 | 简述，100字以内 |
| diagnosis | 诊断 | |
| treatment_plan | 治疗方案 | 摘要 |
| medications | 用药 | 多项用分号分隔 |

### E2. 处方单 (prescription)
*(Sheet: `处方单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| patient_name | 患者姓名 | |
| gender | 性别 | |
| age | 年龄 | |
| prescription_date | 开具日期 | YYYY-MM-DD |
| hospital | 医疗机构 | |
| department | 科室 | |
| doctor | 处方医生 | |
| diagnosis | 临床诊断 | |
| medications | 药品名称 | 多项用分号分隔 |
| dosage | 剂量 | 对应 medications |
| usage | 用法 | 如 口服 tid |
| duration | 疗程 | 如 7天 |

### E3. 检验/检查报告 (lab-report)
*(Sheet: `检验检查报告`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| report_no | 报告编号 | |
| patient_id | 患者ID | |
| test_date | 检查日期 | YYYY-MM-DD |
| test_items | 检测项目 | 分号分隔 |
| results | 结果值 | 分号分隔，对应项目 |
| reference_ranges | 参考范围 | 分号分隔 |
| abnormal_flags | 异常标识 | ↑/↓/正常 |
| critical_value | 危急值标记 | 是/否 |
| reviewer | 审核医师 | |

### E4. 体检报告 (health-checkup)
*(Sheet: `体检报告`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| checkup_no | 体检编号 | |
| check_date | 体检日期 | YYYY-MM-DD |
| dept_items | 科室/项目 | 分号分隔 |
| indicators | 指标值 | 分号分隔 |
| normal_abnormal | 正常/异常 | 分号分隔 |
| health_advice | 健康建议 | 摘要 |
| overall_risk | 总体风险等级 | 高/中/低 |
| doctor | 总检医师 | |

---

## F. 保险类 (insurance)

### F1. 保单 (insurance-policy)
*(Sheet: `保单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| policy_number | 保单号 | |
| insurance_company | 保险公司 | |
| insurance_type | 险种 | 寿险/车险/财产险等 |
| insured_name | 被保险人 | |
| insured_id | 被保险人证件号 | |
| policyholder | 投保人 | |
| coverage_amount | 保额 | 数值 |
| premium | 保费 | 数值 |
| payment_frequency | 缴费方式 | 年缴/月缴/趸缴 |
| effective_date | 生效日期 | YYYY-MM-DD |
| expiry_date | 到期日期 | YYYY-MM-DD |
| beneficiary | 受益人 | |

### F2. 理赔申请 (insurance-claim)
*(Sheet: `理赔申请`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| claim_number | 理赔编号 | |
| policy_number | 关联保单号 | |
| claimant | 申请人 | |
| incident_date | 出险日期 | YYYY-MM-DD |
| incident_type | 出险类型 | 意外/疾病/车祸等 |
| incident_description | 事故描述 | 摘要，150字以内 |
| claim_amount | 申请金额 | 数值 |
| hospital | 就诊医院 | 如适用 |
| supporting_docs | 附件材料 | 列出提交的证明文件 |
| claim_date | 申请日期 | YYYY-MM-DD |

### F3. 理赔结案通知 (claim-settlement)
*(Sheet: `理赔结案通知`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| claim_no | 理赔编号 | |
| policy_no | 关联保单号 | |
| settlement_date | 结案日期 | YYYY-MM-DD |
| approved_amount | 核定赔付金额 | 数值 |
| deductible | 免赔额 | 数值 |
| payment_method | 支付方式 | 银行转账/支票等 |
| closure_reason | 结案原因 | 赔付/拒赔/撤诉 |
| insurer_signature | 保险公司签章 | 文本或“有/无” |

---

## G. 物流类 (logistics)

### G1. 运单 (waybill)
*(Sheet: `运单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| waybill_number | 运单号 | |
| carrier | 承运方 | 物流公司名称 |
| shipper | 发货人 | |
| shipper_address | 发货地址 | |
| consignee | 收货人 | |
| consignee_address | 收货地址 | |
| goods_description | 货物描述 | |
| quantity | 件数 | 整数 |
| weight | 重量(kg) | 数值 |
| freight | 运费 | 数值 |
| shipment_date | 发货日期 | YYYY-MM-DD |
| delivery_date | 预计到达日期 | YYYY-MM-DD |

### G2. 提单 (bill-of-lading)
*(Sheet: `提单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| bl_number | 提单号 | |
| bl_type | 提单类型 | 正本/副本/电放 |
| shipper | 托运人 | |
| consignee | 收货人 | |
| notify_party | 通知方 | |
| vessel_name | 船名 | |
| voyage | 航次 | |
| port_of_loading | 装货港 | |
| port_of_discharge | 卸货港 | |
| container_number | 集装箱号 | 多个用分号分隔 |
| seal_number | 铅封号 | |
| goods_description | 货物描述 | |
| gross_weight | 毛重(kg) | 数值 |
| measurement | 体积(CBM) | 数值 |
| issue_date | 签发日期 | YYYY-MM-DD |
| number_of_originals | 正本份数 | 通常 3 |

### G3. 报关单 (customs-declaration)
*(Sheet: `报关单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| declaration_no | 报关单号 | |
| customs_code | 海关编码 | |
| importer | 进口商 | |
| exporter | 出口商 | |
| trade_mode | 贸易方式 | 一般贸易/加工贸易等 |
| goods_name | 货物名称 | |
| hs_code | HS编码 | |
| declared_value | 申报价值 | 数值 |
| currency | 币种 | USD/CNY等 |
| port | 口岸 | |
| declaration_date | 申报日期 | YYYY-MM-DD |

---

## H. 技术与运维类 (tech-ops) 🆕

### H1. 系统日志 (system-log)
*(Sheet: `系统日志`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| timestamp | 时间戳 | YYYY-MM-DD HH:MM:SS |
| log_level | 日志级别 | INFO/WARN/ERROR/FATAL |
| service_name | 服务/模块名 | |
| trace_id | 追踪ID | 用于链路追踪 |
| error_code | 错误码 | 如有 |
| ip_address | IP地址 | 来源或目标 |
| message_summary | 消息摘要 | ≤200字 |
| stack_trace | 堆栈关键行 | 截取关键报错 |

### H2. 漏洞扫描报告 (vulnerability-report)
*(Sheet: `漏洞扫描报告`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| report_id | 报告编号 | |
| scan_date | 扫描时间 | YYYY-MM-DD |
| target_system | 目标系统/IP | |
| vuln_name | 漏洞名称 | |
| cve_id | CVE编号 | 如有 |
| risk_level | 风险等级 | 高/中/低/信息 |
| affected_component | 影响组件 | |
| remediation | 修复建议 | 摘要 |
| status | 修复状态 | 未修复/已修复/忽略 |

### H3. 服务器监控报表 (server-monitoring)
*(Sheet: `服务器监控报表`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| host_name | 主机名/IP | |
| monitor_time | 监控时间 | YYYY-MM-DD HH:MM |
| cpu_usage | CPU使用率(%) | 数值 |
| mem_usage | 内存使用率(%) | 数值 |
| disk_io | 磁盘IO(MB/s) | 数值 |
| network_traffic | 网络流量(Mbps) | 数值 |
| alert_events | 告警事件数 | 整数 |
| sla_availability | 可用性SLA(%) | 数值 |

---

## I. 客服与销售类 (sales-service) 🆕

### I1. 客诉/工单记录 (customer-ticket)
*(Sheet: `客诉工单记录`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| ticket_id | 工单号 | |
| customer_id | 客户ID | |
| create_time | 创建时间 | YYYY-MM-DD HH:MM |
| category | 问题分类 | 产品/物流/售后/账单等 |
| priority | 紧急程度 | P1/P2/P3/P4 |
| handler | 处理人 | |
| sla_hours | 解决时长(小时) | 数值 |
| csat_score | 满意度评分 | 1-5分 |
| status | 工单状态 | 待处理/处理中/已关闭 |

### I2. 销售报价单 (sales-quotation)
*(Sheet: `销售报价单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| quote_no | 报价单号 | |
| quote_date | 报价日期 | YYYY-MM-DD |
| customer_name | 客户名称 | |
| sales_rep | 销售代表 | |
| items | 产品/服务 | 分号分隔 |
| unit_price | 单价 | 对应items |
| quantity | 数量 | 对应items |
| total_amount | 报价总额 | 数值 |
| valid_until | 报价有效期 | YYYY-MM-DD |
| terms | 商务条款 | 摘要 |

### I3. 售后退换货单 (return-exchange)
*(Sheet: `售后退换货单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| return_no | 退换单号 | |
| original_order | 原订单号 | |
| apply_date | 申请日期 | YYYY-MM-DD |
| reason | 退换原因 | 质量/错发/七天无理由等 |
| items | 退换商品 | 分号分隔 |
| refund_amount | 退款金额 | 数值 |
| logistics_no | 退回物流单号 | |
| approval_status | 审批状态 | 待审/通过/驳回 |

---

## J. 政务与合规类 (gov-compliance) 🆕

### J1. 招投标文件 (bidding-doc)
*(Sheet: `招投标文件`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| project_no | 项目编号 | |
| tenderer | 招标方 | |
| bidder | 投标方 | |
| bid_date | 开标日期 | YYYY-MM-DD |
| bid_price | 投标报价 | 数值 |
| tech_summary | 技术方案摘要 | ≤200字 |
| qualification | 资质证明 | 列出核心资质 |
| evaluation_score | 评标得分 | 数值 |
| result | 中标状态 | 中标/未中标/流标 |

### J2. 政务审批单 (gov-approval)
*(Sheet: `政务审批单`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| approval_no | 审批单号 | |
| applicant | 申请人/企业 | |
| matter | 申请事项 | |
| submit_date | 提交日期 | YYYY-MM-DD |
| process_nodes | 审批环节 | 分号分隔 |
| result | 批复结果 | 通过/驳回/补正 |
| valid_period | 有效期 | YYYY-MM-DD 至 YYYY-MM-DD |
| attachments | 附件清单 | 分号分隔 |

### J3. 合规审计报告 (compliance-audit)
*(Sheet: `合规审计报告`)*

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| audit_target | 审计对象 | |
| audit_period | 审计期间 | |
| auditor | 审计机构 | |
| high_issues | 高风险问题数 | 整数 |
| medium_issues | 中风险问题数 | 整数 |
| low_issues | 低风险问题数 | 整数 |
| rectification_status | 整改状态 | 未开始/进行中/已完成 |
| conclusion | 审计结论 | 摘要 |
| rating | 合规评级 | A/B/C/D |

---

## 未识别类 (unrecognized)

Sheet 名：`未识别`

无法匹配任何预定义子类型的文档归入此类。

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| raw_text_preview | 内容预览 | parsedText 前 300 字符 |
| possible_type | 疑似类型 | agent 的最佳猜测（如有） |
| confidence | 置信度 | 高/中/低 |
| reason | 未识别原因 | 内容模糊/类型未覆盖/OCR质量差 |

## 解析失败类 (parse-failed)

Sheet 名：`解析失败`

document-parser API 返回 status=failed 的文件。

| 字段名 | 中文表头 | 说明 |
|--------|---------|------|
| error_message | 错误信息 | API 返回的 errorMessage |
| file_type | 文件类型 | 文件扩展名 |
| file_size | 文件大小 | KB/MB |

---

## 📐 分类决策指引（V2.0 更新版）

### 核心优先级规则
1. **标题/抬头优先**：发票/回单/对账单/报销单 → A组；合同/协议 → 按内容判定归属（劳动→B2，采购→C1，其他→A5/D4）
2. **金额单据路由**：含税额/税号 → A1；含流水号/账户 → A2/A3；含报销明细 → A4；无税号仅金额 → A8
3. **证照/资质**：营业执照/身份证/护照/许可证 → D组，不混入财务
4. **医疗 vs 保险**：病历/处方/检验/体检 → E组；保单/理赔/结案 → F组
5. **技术/运维**：日志/漏洞/监控 → H组；客服/销售/退换 → I组；招投标/审批/审计 → J组

### 边界 Case 处理
6. **收据 vs 发票**：无税号/无税额 → A8；有完整税务信息 → A1
7. **红字/负数单据**：仍归原类，金额填负值，类型字段标注“红字/冲正”
8. **多页复合文档**：按首页/核心业务分类，在 `remarks` 或 `key_terms` 标注“含多类型附件”
9. **OCR 质量低/置信度不足**：强制归入 `unrecognized`，禁止强行提取
10. **空白/无文本/纯图片**：归入 `parse-failed` 或 `unrecognized`（视解析API返回状态）

### 多语言映射（新增）
| 英文/外文 | 对应分类 | 备注 |
|-----------|----------|------|
| Commercial Invoice / Tax Invoice | A1 | 国际发票结构类似 |
| Bank Statement / Advice | A2/A3 | 按明细或汇总区分 |
| Payslip / Salary Advice | B4 | |
| Purchase Order (PO) / Sales Order (SO) | C1 / I2 | SO 归报价单或订单 |
| Delivery Note / Packing List | C2 | |
| Certificate of Analysis (COA) | C4 | |
| Bill of Lading (B/L) / AWB | G2 / G1 | |
| System Log / Error Log | H1 | |
| Vulnerability Scan Report | H2 | |
| Customer Ticket / Case | I1 | |
| Bidding Document / Tender | J1 | |
| Audit Report / Compliance Review | J3 | |

### 动态扩展机制
若文档明确不属于现有 37 类但可识别性质：
1. 创建新子类型，Sheet 名 ≤31 字符
2. 至少定义 5 个核心字段（含 1 个日期/金额/状态类分析字段）
3. 提交字段定义供业务方确认后纳入路由表

---
