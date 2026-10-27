# Success Verification Method

## 1. Query Completeness

- Aliyun CLI version is 3.3.3 or later, and `cbn` and `vpc` commands are available.
- The credential profile is valid, and every call is read-only.
- Every PageNumber/NextToken pagination has been queried to the end.
- Permission or API failures have been recorded with error code, RequestId, and uncovered scope.

If any critical query failed, the overall result can only be "Partially complete / Unable to confirm", never "All healthy".

## 2. Topology Coverage

Checklist:

- [ ] CEN and the target VBR are located
- [ ] CEN 1.0, CEN 2.0, or "Unable to confirm" is determined for each target region
- [ ] All related TRs and regions are listed
- [ ] Peer/VPC/VBR/VPN Attachments are listed
- [ ] Same-region and cross-region TRs of the target VBR are covered
- [ ] System and custom route tables of each TR are covered
- [ ] System and custom route tables of related VPCs are covered

## 3. Route Evidence

For each confirmed IDC CIDR:

1. Find the primary path evidence in the TR or CEN 1.0 route table.
2. Find evidence of a second equal-cost or standby path according to the expected mode.
3. Record Active, Standby, Candidate, Rejected, and Prohibited states.
4. Confirm the down-cloud path to CEN/TR in the VPC route table.
5. Confirm that Route Maps and conflicting routes do not break the expected redundancy.

## 4. Mode Acceptance

| Mode | Acceptance Condition |
|---|---|
| `dual-vbr-ecmp` | Each IDC CIDR has at least two valid, expected, equal-cost VBR paths |
| `dual-vbr-active-standby` | The primary path is valid and the standby VBR path has verifiable candidate/standby or policy evidence |
| `vbr-vpn-active-standby` | Both the VBR and VPN end-to-end paths have complete topology and route evidence |

## 5. Report Acceptance

The report MUST include:

- Basic information and the inspection boundary confirmed by the user
- Topology coverage with one row per attachment type (VPC, VBR, VPN, Peer), including count, status, and cross-region peer region
- Per-entry route table results
- Route Map and conflicting route impact
- API errors, permission issues, and uncovered resources
- PBR items requiring manual confirmation
- Conclusion that names every attachment type (VPC, VBR, VPN, cross-region Peer) with its verdict, and failover verification recommendations

The complete report MUST appear in the final chat reply itself, in the language of the user's request; a saved report file, a short summary, or a file path alone does not pass acceptance.

A configuration check only proves current configuration evidence, not guaranteed convergence during a failure; final recommendations should include a controlled failover drill.
