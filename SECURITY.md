# Security Policy

## Supported versions

Spendly is an academic/pilot project without a published security-maintenance
schedule or long-term-support release line. As of 14 November 2026, GitHub lists
no public releases or tags. An unpublished `v1.4.1` draft pre-release exists for
maintainer review. Version strings, draft releases, and historical tester APKs
do not establish security support or the deployed revision.

| Version or component | Security-report scope |
| --- | --- |
| Current `main` source | Primary reference for reproducing and reviewing reports |
| Older commits, tester APKs, and hosted deployments | Include the exact version/revision; no guaranteed backports or maintenance window |
| Research notebooks and model artifacts | Report unsafe loading, exposed data, or secrets; research status does not imply production support |

There is no guaranteed response time, fix deadline, bug bounty, or assurance
that any version is vulnerability-free.

## Reporting a vulnerability

**Do not submit sensitive vulnerabilities, exploit details, credentials, or
private financial information in public issues, pull requests, or comments.**

A dedicated private reporting channel has not yet been configured and no
security email address is published. Until a private channel is arranged:

1. Open an issue in the
   [Spendly issue tracker](https://github.com/Eeshan-Vaghjiani/Spendly/issues)
   titled **Private security contact requested**. Include only a request for
   confidential contact, without affected endpoints, impact, reproduction steps,
   attachments, credentials, or personal information. This is a contact request,
   not a vulnerability report.
2. Wait for the repository maintainer to arrange a private channel. Do not send
   details through the issue thread. If no private route is available, keep the
   details confidential rather than posting them publicly.
3. Once the private channel is agreed, provide the affected commit/app/API
   version, component, prerequisites, potential impact, and a minimal
   reproduction using synthetic data and accounts you control. Include sanitized
   logs or a proposed fix where useful, never live secrets or other users' data.

The repository owner must confirm a durable private reporting method before this
temporary contact process can be replaced. See the pending decisions in
[community setup](docs/community_setup.md).

## What to report

- Authentication or session problems: password/Google sign-in bypass, JWT
  validation or revocation, insecure token storage, or account-switching leaks.
- Unauthorized financial access or modification: transactions, budgets,
  forecasts, alerts, recommendations, uploads, exports, or account deletion.
- API access-control, validation, injection, upload-handling, or cross-user
  ownership failures, including the separate admin session and CSRF boundary.
- Exposed secrets: signing material, service credentials, database URLs,
  administrator passwords, tokens, or sensitive logs/configuration.
- Vulnerable dependencies, unsafe model deserialization, or data exposure
  through model/research artifacts that affects Spendly.

## Responsible investigation and disclosure

Use a local, disposable environment with synthetic records. Do not test against
a hosted service or another person's account without explicit authorization.
Avoid service disruption and do not extract or alter private records. If you
encounter real financial information or a live credential, stop, do not copy it
into a report, and arrange private contact. The authorized operator should handle
credential rotation and incident response.

After receiving a private report, maintainers should assess impact, request any
needed reproduction details, and coordinate remediation and disclosure with the
reporter. Agree on public timing and attribution before sharing details; public
summaries must omit secrets and personal data. This policy is not authorization
to access third-party systems or a promise of legal safe harbor.

For implementation context, see [security and privacy](docs/security_and_privacy.md),
[administrator safeguards](docs/admin_management.md), and
[deployment limitations](docs/live_deployment_and_tester_apk.md). These documents
describe scoped controls and requirements, not audited security guarantees.
