# Document Classification System — Detailed Field Definitions (V2.0)

This file defines **10 classification groups and 37 document subtypes** along with their standard extraction fields. The Agent MUST refer to this file when extracting text fields and performing consolidation.

**Field naming rules**: English `snake_case`. Excel headers use localized names (with English field names in parentheses). In each subtype's field list, `filename` (source file name) is an implicit first column and does not need to be defined here.

---

## A. Finance & Tax (finance-tax)

### A1. VAT Invoice (vat-invoice)
*(Sheet: `VAT Invoice`)*

| Field Name | Header | Description |
|--------|---------|------|
| invoice_type | Invoice Type | Special/General/Electronic/Red-letter |
| invoice_code | Invoice Code | 10-12 digits |
| invoice_number | Invoice Number | 8 digits |
| date | Invoice Date | YYYY-MM-DD |
| buyer_name | Buyer Name | |
| buyer_tax_id | Buyer Tax ID | |
| seller_name | Seller Name | |
| seller_tax_id | Seller Tax ID | |
| items | Goods/Service Name | Multiple items separated by semicolons |
| amount_before_tax | Amount Before Tax | Numeric, 2 decimal places |
| tax_rate | Tax Rate | e.g. 13%, 9%, 6% |
| tax_amount | Tax Amount | Numeric |
| total_amount | Total Amount (incl. Tax) | Numeric |
| remarks | Remarks | |

### A2. Bank Receipt (bank-receipt)
*(Sheet: `Bank Receipt`)*

| Field Name | Header | Description |
|--------|---------|------|
| bank_name | Bank Name | |
| serial_number | Serial/Voucher No. | |
| transaction_date | Transaction Date | YYYY-MM-DD |
| payer_name | Payer Name | |
| payer_account | Payer Account | |
| payee_name | Payee Name | |
| payee_account | Payee Account | |
| amount | Transaction Amount | Numeric |
| currency | Currency | Default CNY |
| transaction_type | Transaction Type | Transfer/Remittance/Agency payment, etc. |
| purpose | Purpose/Summary | |

### A3. Bank Statement (bank-statement)
*(Sheet: `Bank Statement`)*

| Field Name | Header | Description |
|--------|---------|------|
| bank_name | Bank Name | |
| account_number | Account Number | |
| account_name | Account Name | |
| statement_period | Statement Period | e.g. 2026-01 to 2026-03 |
| opening_balance | Opening Balance | Numeric |
| closing_balance | Closing Balance | Numeric |
| total_debit | Total Debit | Numeric |
| total_credit | Total Credit | Numeric |
| transaction_count | Transaction Count | Integer |

### A4. Expense Claim (expense-claim)
*(Sheet: `Expense Claim`)*

| Field Name | Header | Description |
|--------|---------|------|
| applicant | Applicant | |
| department | Department | |
| claim_date | Claim Date | YYYY-MM-DD |
| expense_items | Expense Items | Semicolon-separated |
| total_amount | Claim Amount | Numeric |
| payment_method | Payment Method | Cash/Transfer, etc. |
| approver | Approver | |
| remarks | Remarks | |

### A5. Contract / Agreement (contract)
*(Sheet: `Contract Agreement`)*

| Field Name | Header | Description |
|--------|---------|------|
| contract_number | Contract Number | |
| contract_title | Contract Title | |
| party_a | Party A | |
| party_b | Party B | |
| contract_type | Contract Type | Procurement/Service/Lease/Other |
| effective_date | Effective Date | YYYY-MM-DD |
| expiry_date | Expiry Date | YYYY-MM-DD |
| contract_value | Contract Value | Numeric |
| currency | Currency | Default CNY |
| key_terms | Key Terms | Summary ≤150 characters |
| signature_date | Signature Date | YYYY-MM-DD |

### A6. Tax Return (tax-return)
*(Sheet: `Tax Return`)*

| Field Name | Header | Description |
|--------|---------|------|
| taxpayer_name | Taxpayer Name | |
| tax_id | Tax ID | |
| declaration_period | Filing Period | YYYY-MM |
| tax_type | Tax Category | VAT/Corporate Income Tax, etc. |
| taxable_amount | Tax Basis | Numeric |
| tax_payable | Tax Payable | Numeric |
| tax_paid | Tax Paid | Numeric |
| deduction_amount | Tax Exemption Amount | Numeric |
| declaration_status | Filing Status | Filed/Unfiled/Amended |

### A7. Financial Statement (financial-statement)
*(Sheet: `Financial Statement`)*

| Field Name | Header | Description |
|--------|---------|------|
| company_name | Company Name | |
| report_period | Reporting Period | e.g. 2025-Q3 |
| total_assets | Total Assets | Numeric |
| total_liabilities | Total Liabilities | Numeric |
| equity | Equity | Numeric |
| revenue | Revenue | Numeric |
| net_profit | Net Profit | Numeric |
| cash_flow_operating | Operating Cash Flow | Numeric |
| audit_opinion | Audit Opinion | Unqualified/Qualified/Adverse, etc. |

### A8. Receipt / Payment Voucher (receipt-payment)
*(Sheet: `Receipt Payment Voucher`)*

| Field Name | Header | Description |
|--------|---------|------|
| receipt_number | Receipt Number | |
| date | Receipt Date | YYYY-MM-DD |
| payer | Payer | |
| payee | Payee | |
| amount | Amount | Numeric |
| payment_method | Payment Method | Cash/Transfer/Check, etc. |
| purpose | Payment Purpose | |
| issuer_signature | Issuer Signature | Text or "Yes/No" |

---

## B. Human Resources (hr)

### B1. Resume (resume)
*(Sheet: `Resume`)*

| Field Name | Header | Description |
|--------|---------|------|
| name | Full Name | |
| gender | Gender | |
| birth_date | Date of Birth | YYYY-MM-DD or age |
| phone | Phone | |
| email | Email | |
| highest_education | Highest Education | Bachelor/Master/PhD, etc. |
| school | University | School of highest degree |
| major | Major | |
| work_years | Years of Experience | |
| latest_company | Latest Employer | |
| latest_position | Latest Position | |
| skills | Skill Tags | Semicolon-separated |
| expected_salary | Expected Salary | If available |

### B2. Labor Contract (labor-contract)
*(Sheet: `Labor Contract`)*

| Field Name | Header | Description |
|--------|---------|------|
| employee_name | Employee Name | |
| id_number | ID Number | |
| employer_name | Employer | |
| contract_type | Contract Type | Fixed-term/Open-ended/Task-based |
| start_date | Contract Start Date | YYYY-MM-DD |
| end_date | Contract End Date | YYYY-MM-DD |
| position | Position | |
| work_location | Work Location | |
| salary | Salary | Numeric or description |
| probation_period | Probation Period | e.g. 3 months |
| probation_salary | Probation Salary | |
| signature_date | Signing Date | YYYY-MM-DD |

### B3. Resignation Certificate (resignation-cert)
*(Sheet: `Resignation Certificate`)*

| Field Name | Header | Description |
|--------|---------|------|
| employee_name | Employee Name | |
| id_number | ID Number | |
| company_name | Company Name | |
| position | Position | |
| entry_date | Start Date | YYYY-MM-DD |
| leave_date | Departure Date | YYYY-MM-DD |
| leave_reason | Reason for Leaving | If available |
| issue_date | Issue Date | YYYY-MM-DD |

### B4. Payslip (payslip)
*(Sheet: `Payslip`)*

| Field Name | Header | Description |
|--------|---------|------|
| employee_name | Employee Name | |
| employee_id | Employee ID | |
| pay_period | Pay Cycle | e.g. 2026-03 |
| base_salary | Base Salary | Numeric |
| allowances | Allowances/Subsidies | Numeric |
| overtime_pay | Overtime Pay | Numeric |
| bonus | Bonus | Numeric |
| gross_pay | Gross Salary | Numeric |
| social_insurance | Social Insurance Deduction | Numeric |
| housing_fund | Housing Fund Deduction | Numeric |
| tax | Income Tax Deduction | Numeric |
| other_deductions | Other Deductions | Numeric |
| net_pay | Net Salary | Numeric |

### B5. Attendance Record (attendance-record)
*(Sheet: `Attendance Record`)*

| Field Name | Header | Description |
|--------|---------|------|
| employee_id | Employee ID | |
| date | Date | YYYY-MM-DD |
| clock_in | Clock In Time | HH:MM |
| clock_out | Clock Out Time | HH:MM |
| work_hours | Work Hours | Numeric |
| status | Anomaly Status | Normal/Late/Early leave/Missing punch/Leave |
| department | Department | |

### B6. Training Certificate (training-cert)
*(Sheet: `Training Certificate`)*

| Field Name | Header | Description |
|--------|---------|------|
| trainee_name | Trainee Name | |
| course_name | Course Name | |
| training_org | Training Institution | |
| issue_date | Issue Date | YYYY-MM-DD |
| valid_until | Valid Until | YYYY-MM-DD |
| certificate_no | Certificate ID | |
| credits_hours | Credits/Hours | Numeric |

### B7. Performance Review (performance-review)
*(Sheet: `Performance Review`)*

| Field Name | Header | Description |
|--------|---------|------|
| employee_id | Employee ID | |
| review_period | Review Period | e.g. 2025-Q3 |
| kpi_scores | KPI Score | Metric:Score, semicolon-separated |
| overall_rating | Overall Rating | S/A/B/C/D |
| manager_comments | Supervisor Comment | Summary |
| next_goals | Next Period Target | Summary |
| review_date | Review Date | YYYY-MM-DD |

---

## C. Supply Chain & Procurement (supply-chain)

### C1. Purchase Order (purchase-order)
*(Sheet: `Purchase Order`)*

| Field Name | Header | Description |
|--------|---------|------|
| po_number | Order Number | |
| date | Order Date | YYYY-MM-DD |
| supplier | Supplier | |
| buyer | Purchaser | |
| items | Material/Product | Multiple items separated by semicolons |
| quantities | Quantity | Corresponding to items |
| unit_prices | Unit Price | Corresponding to items |
| total_amount | Total Amount | Numeric |
| currency | Currency | Default CNY |
| delivery_date | Delivery Date | YYYY-MM-DD |
| payment_terms | Payment Terms | |

### C2. Delivery Note (delivery-note)
*(Sheet: `Delivery Note`)*

| Field Name | Header | Description |
|--------|---------|------|
| delivery_number | Delivery Note No. | |
| date | Delivery Date | YYYY-MM-DD |
| supplier | Supplier/Shipper | |
| receiver | Receiver | |
| items | Goods Name | Multiple items separated by semicolons |
| quantities | Quantity | Corresponding to items |
| delivery_address | Delivery Address | |
| receiver_name | Signee | |
| related_po | Related PO No. | If available |

### C3. Warehouse Receipt (warehouse-receipt)
*(Sheet: `Warehouse Receipt`)*

| Field Name | Header | Description |
|--------|---------|------|
| receipt_number | Warehouse Receipt No. | |
| date | Receipt Date | YYYY-MM-DD |
| supplier | Supplier | |
| warehouse | Receiving Warehouse | |
| items | Material Name | Multiple items separated by semicolons |
| quantities | Quantity | Corresponding to items |
| inspector | Acceptance Inspector | |
| related_po | Related PO No. | If available |
| remarks | Remarks | |

### C4. Quality Inspection Report (quality-report)
*(Sheet: `Quality Inspection Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| report_number | Report Number | |
| date | Test Date | YYYY-MM-DD |
| product_name | Product Name | |
| batch_number | Batch No. | |
| specification | Specification | |
| test_items | Test Item | Multiple items separated by semicolons |
| test_results | Test Result | Corresponding to test_items |
| conclusion | Conclusion | Pass/Fail |
| inspector | Inspector | |
| issuing_org | Issuing Institution | |

### C5. Supplier Evaluation (supplier-evaluation)
*(Sheet: `Supplier Evaluation`)*

| Field Name | Header | Description |
|--------|---------|------|
| supplier_name | Supplier Name | |
| evaluation_period | Evaluation Cycle | e.g. 2025-Q3 |
| quality_score | Quality Score | 1-10 |
| delivery_score | Delivery Score | 1-10 |
| cost_score | Price Score | 1-10 |
| service_score | Service Score | 1-10 |
| overall_rating | Overall Rating | A/B/C/D |
| risk_level | Risk Level | High/Medium/Low |
| evaluator | Evaluator | |

### C6. Inventory Count (inventory-count)
*(Sheet: `Inventory Count`)*

| Field Name | Header | Description |
|--------|---------|------|
| warehouse | Warehouse Name | |
| location_code | Bin Code | |
| item_code | Material Code | |
| book_qty | Book Quantity | Numeric |
| actual_qty | Actual Count | Numeric |
| variance_qty | Variance | Numeric |
| variance_reason | Variance Reason | Summary |
| count_date | Count Date | YYYY-MM-DD |
| counter | Counter | |

---

## D. Administrative & Legal (admin-legal)

### D1. Business License (business-license)
*(Sheet: `Business License`)*

| Field Name | Header | Description |
|--------|---------|------|
| company_name | Company Name | |
| unified_credit_code | Unified Social Credit Code | 18 digits |
| legal_representative | Legal Representative | |
| company_type | Company Type | Limited Liability/Joint Stock, etc. |
| registered_capital | Registered Capital | |
| establishment_date | Establishment Date | YYYY-MM-DD |
| business_scope | Business Scope | Summary, within 200 characters |
| address | Registered Address | |
| valid_period | Business Term | |

### D2. ID Card (id-card)
*(Sheet: `ID Card`)*

| Field Name | Header | Description |
|--------|---------|------|
| name | Full Name | |
| gender | Gender | Male/Female |
| ethnicity | Ethnicity | |
| birth_date | Date of Birth | YYYY-MM-DD |
| address | Address | |
| id_number | ID Card Number | 18 digits |
| issuing_authority | Issuing Authority | |
| valid_period | Validity Period | Start and end dates |

### D3. Passport (passport)
*(Sheet: `Passport`)*

| Field Name | Header | Description |
|--------|---------|------|
| name_cn | Chinese Name | |
| name_en | English Name | |
| nationality | Nationality | |
| gender | Gender | |
| birth_date | Date of Birth | YYYY-MM-DD |
| birth_place | Place of Birth | |
| passport_number | Passport Number | |
| issue_date | Issue Date | YYYY-MM-DD |
| expiry_date | Valid Until | YYYY-MM-DD |
| issuing_authority | Issuing Authority | |

### D4. Non-Disclosure Agreement (nda)
*(Sheet: `Non-Disclosure Agreement`)*

| Field Name | Header | Description |
|--------|---------|------|
| party_a | Party A | |
| party_b | Party B | |
| sign_date | Signature Date | YYYY-MM-DD |
| confidential_period | Confidentiality Period | e.g. 3 years/Permanent |
| scope_summary | Confidentiality Scope Summary | ≤150 characters |
| penalty_clause | Breach Compensation Clause | Summary |
| governing_law | Governing Law | |

### D5. Qualification License (qualification-license)
*(Sheet: `Qualification License`)*

| Field Name | Header | Description |
|--------|---------|------|
| cert_number | Certificate ID | |
| holder_name | License Holder | |
| issuing_authority | Issuing Authority | |
| issue_date | Certificate Date | YYYY-MM-DD |
| expiry_date | Valid Until | YYYY-MM-DD |
| license_scope | License Scope | Summary |
| status | Status | Valid/Revoked/Expired |

### D6. Official Notice (official-notice)
*(Sheet: `Official Notice`)*

| Field Name | Header | Description |
|--------|---------|------|
| doc_number | Document Number | |
| issuing_dept | Issuing Authority | |
| title | Title | |
| publish_date | Published Date | YYYY-MM-DD |
| target_audience | To/CC Recipients | |
| content_summary | Summary | ≤200 characters |
| urgency | Urgency Level | Urgent/Priority/Routine |
| confidential_level | Classification Level | Top Secret/Secret/Confidential/Public |

---

## E. Medical (medical)

### E1. Medical Record (medical-record)
*(Sheet: `Medical Record`)*

| Field Name | Header | Description |
|--------|---------|------|
| patient_name | Patient Name | |
| gender | Gender | |
| age | Age | |
| visit_date | Visit Date | YYYY-MM-DD |
| hospital | Medical Institution | |
| department | Department | |
| doctor | Attending Doctor | |
| chief_complaint | Chief Complaint | Brief description, within 100 characters |
| diagnosis | Diagnosis | |
| treatment_plan | Treatment Plan | Summary |
| medications | Medication | Multiple items separated by semicolons |

### E2. Prescription (prescription)
*(Sheet: `Prescription`)*

| Field Name | Header | Description |
|--------|---------|------|
| patient_name | Patient Name | |
| gender | Gender | |
| age | Age | |
| prescription_date | Issue Date | YYYY-MM-DD |
| hospital | Medical Institution | |
| department | Department | |
| doctor | Prescribing Doctor | |
| diagnosis | Clinical Diagnosis | |
| medications | Drug Name | Multiple items separated by semicolons |
| dosage | Dosage | Corresponding to medications |
| usage | Usage | e.g. Oral tid |
| duration | Treatment Course | e.g. 7 days |

### E3. Lab / Examination Report (lab-report)
*(Sheet: `Lab Test Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| report_no | Report Number | |
| patient_id | Patient ID | |
| test_date | Examination Date | YYYY-MM-DD |
| test_items | Test Item | Semicolon-separated |
| results | Result Value | Semicolon-separated, corresponding to items |
| reference_ranges | Reference Range | Semicolon-separated |
| abnormal_flags | Anomaly Flag | ↑/↓/Normal |
| critical_value | Critical Value Flag | Yes/No |
| reviewer | Reviewing Doctor | |

### E4. Health Checkup Report (health-checkup)
*(Sheet: `Medical Exam Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| checkup_no | Exam ID | |
| check_date | Exam Date | YYYY-MM-DD |
| dept_items | Department/Project | Semicolon-separated |
| indicators | Metric Value | Semicolon-separated |
| normal_abnormal | Normal/Abnormal | Semicolon-separated |
| health_advice | Health Recommendations | Summary |
| overall_risk | Overall Risk Level | High/Medium/Low |
| doctor | Chief Examiner | |

---

## F. Insurance (insurance)

### F1. Insurance Policy (insurance-policy)
*(Sheet: `Insurance Policy`)*

| Field Name | Header | Description |
|--------|---------|------|
| policy_number | Policy Number | |
| insurance_company | Insurance Company | |
| insurance_type | Insurance Type | Life/Auto/Property, etc. |
| insured_name | Insured | |
| insured_id | Insured ID No. | |
| policyholder | Policyholder | |
| coverage_amount | Sum Insured | Numeric |
| premium | Premium | Numeric |
| payment_frequency | Payment Method | Annual/Monthly/Single payment |
| effective_date | Effective Date | YYYY-MM-DD |
| expiry_date | Expiry Date | YYYY-MM-DD |
| beneficiary | Beneficiary | |

### F2. Insurance Claim (insurance-claim)
*(Sheet: `Claim Application`)*

| Field Name | Header | Description |
|--------|---------|------|
| claim_number | Claim Number | |
| policy_number | Related Policy No. | |
| claimant | Applicant | |
| incident_date | Incident Date | YYYY-MM-DD |
| incident_type | Incident Type | Accident/Illness/Car crash, etc. |
| incident_description | Incident Description | Summary, within 150 characters |
| claim_amount | Requested Amount | Numeric |
| hospital | Hospital | If applicable |
| supporting_docs | Attachments | List of submitted supporting documents |
| claim_date | Application Date | YYYY-MM-DD |

### F3. Claim Settlement Notice (claim-settlement)
*(Sheet: `Claim Settlement Notice`)*

| Field Name | Header | Description |
|--------|---------|------|
| claim_no | Claim Number | |
| policy_no | Related Policy No. | |
| settlement_date | Closure Date | YYYY-MM-DD |
| approved_amount | Approved Claim Amount | Numeric |
| deductible | Deductible | Numeric |
| payment_method | Payment Method | Bank transfer/Check, etc. |
| closure_reason | Closure Reason | Paid/Rejected/Withdrawn |
| insurer_signature | Insurance Company Seal | Text or "Yes/No" |

---

## G. Logistics (logistics)

### G1. Waybill (waybill)
*(Sheet: `Waybill`)*

| Field Name | Header | Description |
|--------|---------|------|
| waybill_number | Waybill No. | |
| carrier | Carrier | Logistics company name |
| shipper | Shipper | |
| shipper_address | Shipping Address | |
| consignee | Consignee | |
| consignee_address | Receiving Address | |
| goods_description | Goods Description | |
| quantity | Quantity (pieces) | Integer |
| weight | Weight (kg) | Numeric |
| freight | Freight | Numeric |
| shipment_date | Shipping Date | YYYY-MM-DD |
| delivery_date | Estimated Arrival Date | YYYY-MM-DD |

### G2. Bill of Lading (bill-of-lading)
*(Sheet: `Bill of Lading`)*

| Field Name | Header | Description |
|--------|---------|------|
| bl_number | Bill of Lading No. | |
| bl_type | B/L Type | Original/Copy/Telex release |
| shipper | Shipper/Consignor | |
| consignee | Consignee | |
| notify_party | Notify Party | |
| vessel_name | Vessel Name | |
| voyage | Voyage | |
| port_of_loading | Port of Loading | |
| port_of_discharge | Port of Discharge | |
| container_number | Container No. | Multiple separated by semicolons |
| seal_number | Seal No. | |
| goods_description | Goods Description | |
| gross_weight | Gross Weight (kg) | Numeric |
| measurement | Volume (CBM) | Numeric |
| issue_date | Issue Date | YYYY-MM-DD |
| number_of_originals | Original Copies | Usually 3 |

### G3. Customs Declaration (customs-declaration)
*(Sheet: `Customs Declaration`)*

| Field Name | Header | Description |
|--------|---------|------|
| declaration_no | Customs Declaration No. | |
| customs_code | Customs Code | |
| importer | Importer | |
| exporter | Exporter | |
| trade_mode | Trade Mode | General trade/Processing trade, etc. |
| goods_name | Goods Name | |
| hs_code | HS Code | |
| declared_value | Declared Value | Numeric |
| currency | Currency | USD/CNY, etc. |
| port | Port | |
| declaration_date | Filing Date | YYYY-MM-DD |

---

## H. Technology & Operations (tech-ops) 🆕

### H1. System Log (system-log)
*(Sheet: `System Log`)*

| Field Name | Header | Description |
|--------|---------|------|
| timestamp | Timestamp | YYYY-MM-DD HH:MM:SS |
| log_level | Log Level | INFO/WARN/ERROR/FATAL |
| service_name | Service/Module Name | |
| trace_id | Trace ID | For distributed tracing |
| error_code | Error Code | If available |
| ip_address | IP Address | Source or destination |
| message_summary | Message Summary | ≤200 characters |
| stack_trace | Stack Trace Key Line | Extract key error lines |

### H2. Vulnerability Scan Report (vulnerability-report)
*(Sheet: `Vulnerability Scan Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| report_id | Report Number | |
| scan_date | Scan Time | YYYY-MM-DD |
| target_system | Target System/IP | |
| vuln_name | Vulnerability Name | |
| cve_id | CVE ID | If available |
| risk_level | Risk Level | High/Medium/Low/Info |
| affected_component | Affected Components | |
| remediation | Remediation Recommendation | Summary |
| status | Remediation Status | Unpatched/Patched/Ignored |

### H3. Server Monitoring Report (server-monitoring)
*(Sheet: `Server Monitoring Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| host_name | Hostname/IP | |
| monitor_time | Monitoring Time | YYYY-MM-DD HH:MM |
| cpu_usage | CPU Utilization (%) | Numeric |
| mem_usage | Memory Utilization (%) | Numeric |
| disk_io | Disk IO (MB/s) | Numeric |
| network_traffic | Network Traffic (Mbps) | Numeric |
| alert_events | Alert Events Count | Integer |
| sla_availability | Availability SLA (%) | Numeric |

---

## I. Sales & Customer Service (sales-service) 🆕

### I1. Customer Ticket (customer-ticket)
*(Sheet: `Customer Complaint Ticket`)*

| Field Name | Header | Description |
|--------|---------|------|
| ticket_id | Ticket No. | |
| customer_id | Customer ID | |
| create_time | Created Time | YYYY-MM-DD HH:MM |
| category | Issue Category | Product/Logistics/After-sales/Billing, etc. |
| priority | Urgency Level | P1/P2/P3/P4 |
| handler | Handler | |
| sla_hours | Resolution Time (hours) | Numeric |
| csat_score | Satisfaction Score | 1-5 |
| status | Ticket Status | Pending/In Progress/Closed |

### I2. Sales Quotation (sales-quotation)
*(Sheet: `Sales Quotation`)*

| Field Name | Header | Description |
|--------|---------|------|
| quote_no | Quotation No. | |
| quote_date | Quotation Date | YYYY-MM-DD |
| customer_name | Customer Name | |
| sales_rep | Sales Rep | |
| items | Product/Service | Semicolon-separated |
| unit_price | Unit Price | Corresponding to items |
| quantity | Quantity | Corresponding to items |
| total_amount | Total Quotation | Numeric |
| valid_until | Quotation Validity | YYYY-MM-DD |
| terms | Commercial Terms | Summary |

### I3. Return / Exchange (return-exchange)
*(Sheet: `After-sales Return/Exchange`)*

| Field Name | Header | Description |
|--------|---------|------|
| return_no | Return/Exchange No. | |
| original_order | Original Order No. | |
| apply_date | Application Date | YYYY-MM-DD |
| reason | Return/Exchange Reason | Quality/Wrong shipment/7-day no-reason, etc. |
| items | Returned Product | Semicolon-separated |
| refund_amount | Refund Amount | Numeric |
| logistics_no | Return Logistics No. | |
| approval_status | Approval Status | Pending/Approved/Rejected |

---

## J. Government & Compliance (gov-compliance) 🆕

### J1. Bidding Document (bidding-doc)
*(Sheet: `Tender Document`)*

| Field Name | Header | Description |
|--------|---------|------|
| project_no | Project No. | |
| tenderer | Tenderer | |
| bidder | Bidder | |
| bid_date | Bid Opening Date | YYYY-MM-DD |
| bid_price | Bid Price | Numeric |
| tech_summary | Technical Solution Summary | ≤200 characters |
| qualification | Qualification Docs | List core qualifications |
| evaluation_score | Evaluation Score | Numeric |
| result | Bid Award Status | Won/Lost/Void |

### J2. Government Approval (gov-approval)
*(Sheet: `Government Approval Form`)*

| Field Name | Header | Description |
|--------|---------|------|
| approval_no | Approval No. | |
| applicant | Applicant/Company | |
| matter | Application Item | |
| submit_date | Submission Date | YYYY-MM-DD |
| process_nodes | Approval Stage | Semicolon-separated |
| result | Approval Result | Approved/Rejected/Revision required |
| valid_period | Validity Period | YYYY-MM-DD to YYYY-MM-DD |
| attachments | Attachment List | Semicolon-separated |

### J3. Compliance Audit Report (compliance-audit)
*(Sheet: `Compliance Audit Report`)*

| Field Name | Header | Description |
|--------|---------|------|
| audit_target | Audit Target | |
| audit_period | Audit Period | |
| auditor | Audit Firm | |
| high_issues | High Risk Issues | Integer |
| medium_issues | Medium Risk Issues | Integer |
| low_issues | Low Risk Issues | Integer |
| rectification_status | Rectification Status | Not started/In progress/Completed |
| conclusion | Audit Conclusion | Summary |
| rating | Compliance Rating | A/B/C/D |

---

## Unrecognized (unrecognized)

Sheet name: `Unrecognized`

Documents that cannot be matched to any predefined subtype are classified here.

| Field Name | Header | Description |
|--------|---------|------|
| raw_text_preview | Content Preview | First 300 characters of parsedText |
| possible_type | Suspected Type | Agent's best guess (if any) |
| confidence | Confidence | High/Medium/Low |
| reason | Unrecognized Reason | Ambiguous content/Type not covered/Poor OCR quality |

## Parse Failed (parse-failed)

Sheet name: `Parse Failed`

Files where the document-parser API returned status=failed.

| Field Name | Header | Description |
|--------|---------|------|
| error_message | Error Message | errorMessage returned by the API |
| file_type | File Type | File extension |
| file_size | File Size | KB/MB |

---

## 📐 Classification Decision Guide (V2.0 Updated)

### Core Priority Rules
1. **Title/Header first**: Invoice/Receipt/Statement/Expense claim → Group A; Contract/Agreement → Determine by content (Labor → B2, Procurement → C1, Other → A5/D4)
2. **Amount document routing**: Contains tax amount/tax ID → A1; Contains serial number/account → A2/A3; Contains expense details → A4; Amount only without tax ID → A8
3. **Licenses/Qualifications**: Business license/ID card/Passport/Permit → Group D, do not mix into Finance
4. **Medical vs Insurance**: Medical record/Prescription/Lab report/Checkup → Group E; Policy/Claim/Settlement → Group F
5. **Technology/Operations**: Log/Vulnerability/Monitoring → Group H; Customer service/Sales/Returns → Group I; Bidding/Approval/Audit → Group J

### Edge Case Handling
6. **Receipt vs Invoice**: No tax ID/No tax amount → A8; Complete tax information → A1
7. **Red-letter/Negative documents**: Still classified under original type, amount filled as negative, type field annotated with "Red-letter/Reversal"
8. **Multi-page composite documents**: Classify by front page/core business, annotate "Contains multi-type attachments" in `remarks` or `key_terms`
9. **Low OCR quality/Insufficient confidence**: MUST classify as `unrecognized`, MUST NOT force extraction
10. **Blank/No text/Image only**: Classify as `parse-failed` or `unrecognized` (depending on parse API return status)

### Multilingual Mapping (New)
| English/Foreign | Corresponding Classification | Notes |
|-----------|----------|------|
| Commercial Invoice / Tax Invoice | A1 | International invoice structure is similar |
| Bank Statement / Advice | A2/A3 | Distinguish by detail or summary |
| Payslip / Salary Advice | B4 | |
| Purchase Order (PO) / Sales Order (SO) | C1 / I2 | SO maps to quotation or order |
| Delivery Note / Packing List | C2 | |
| Certificate of Analysis (COA) | C4 | |
| Bill of Lading (B/L) / AWB | G2 / G1 | |
| System Log / Error Log | H1 | |
| Vulnerability Scan Report | H2 | |
| Customer Ticket / Case | I1 | |
| Bidding Document / Tender | J1 | |
| Audit Report / Compliance Review | J3 | |

### Dynamic Extension Mechanism
If a document clearly does not belong to the existing 37 types but has identifiable characteristics:
1. Create a new subtype with Sheet name ≤31 characters
2. Define at least 5 core fields (including 1 date/amount/status analytical field)
3. Submit field definitions for business confirmation before adding to the routing table

---
