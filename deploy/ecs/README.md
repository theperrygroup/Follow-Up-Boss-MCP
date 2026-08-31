# ECS Hosted Deployment

This directory contains the minimum AWS deployment assets needed to run the shared
`followupboss-mcp-hosted` entrypoint on ECS/Fargate.

The source-of-truth runtime contract still lives in:

- [`docs/hosted-deployment-guide.md`](../../docs/hosted-deployment-guide.md)
- [`docs/customer-onboarding-flow.md`](../../docs/customer-onboarding-flow.md)
- [`docs/security-incident-playbook.md`](../../docs/security-incident-playbook.md)
- [`docs/multi-tenant-hosting-checklist.md`](../../docs/multi-tenant-hosting-checklist.md)

## Files

- `task-definition.template.json`: ECS task definition template for the hosted server container.
- `task-role-policy.template.json`: least-privilege task-role policy template for hosted secret
  access.

## Placeholder Values

Before registering the task definition, replace the placeholders below:

| Placeholder | Meaning |
| --- | --- |
| `__AWS_ACCOUNT_ID__` | AWS account ID that owns the ECR repository. |
| `__DEPLOYMENT_ENVIRONMENT__` | Hosted deployment environment label. The only supported shared deployment value is `production`. |
| `__FUB_OAUTH_CALLBACK_URL__` | Public callback URL registered on the Follow Up Boss OAuth app, such as `https://fub.theperry.group/oauth/follow-up-boss/callback`. |
| `__FUB_OAUTH_CLIENT_ID__` | Follow Up Boss OAuth client id. |
| `__FUB_OAUTH_CLIENT_SECRET_ARN__` | Secrets Manager ARN whose secret string is the Follow Up Boss OAuth client secret. |
| `__FUB_OAUTH_SYSTEM_KEY_SECRET_ARN__` | Secrets Manager ARN whose secret string is the registered-system key for OAuth-created tenant credentials. |
| `__FUB_OAUTH_SYSTEM_NAME__` | Registered Follow Up Boss system name associated with the OAuth app. |
| `__AWS_REGION__` | AWS region, such as `us-west-1`. |
| `__HOSTED_ISSUER_URL__` | Stable issuer URL for hosted auth, such as the customer portal or control plane. |
| `__HOSTED_RESOURCE_SERVER_URL__` | External HTTPS MCP URL, such as `https://fub.theperry.group/mcp`. |
| `__IMAGE_URI__` | Full ECR image URI, including tag. |
| `__LOG_GROUP_NAME__` | CloudWatch Logs group name for the ECS service. |
| `__REDIS_URL_SECRET_ARN__` | Secrets Manager ARN whose secret string is the complete Redis URL. |
| `__SENTRY_DSN__` | Sentry project DSN for hosted error monitoring. Leave empty to disable Sentry. |
| `__SENTRY_ENVIRONMENT__` | Sentry environment name. The hosted MCP deployment uses `production`. |
| `__SENTRY_RELEASE__` | Sentry release identifier, usually package version plus Git SHA. |
| `__SENTRY_TRACES_SAMPLE_RATE__` | Optional Sentry trace sample rate between `0.0` and `1.0`; leave empty to disable tracing. |
| `__TASK_EXECUTION_ROLE_ARN__` | ECS task execution role ARN. |
| `__TASK_ROLE_ARN__` | ECS task role ARN used by the app at runtime. |
| `__TENANT_DATABASE_URL_SECRET_ARN__` | Secrets Manager ARN whose secret string is the complete PostgreSQL connection URL. |
| `__TENANT_SECRET_PREFIX__` | Tenant secret prefix for the deployed MCP URL. |
| `__TENANT_SECRET_PREFIX_ARN__` | Secrets Manager ARN prefix for the deployed MCP URL's tenant secrets. |
| `__TENANT_SECRET_REGION__` | AWS region for the tenant secret store. |

## Reference ECS Runtime Shape

Use one public Application Load Balancer plus one ECS/Fargate service in the default VPC or an
equivalent trusted VPC. The container should listen on port `8000`, and the ALB should forward
HTTPS traffic for `/mcp` to the task target group over HTTP.

The hosted `/mcp` path intentionally returns `401 invalid_token` to unauthenticated health probes.
That is a healthy hosted response, so the ALB target group matcher should accept `401`.

Recommended resources:

- 1 ECS cluster for the hosted MCP environment
- 1 ECS service for `followupboss-mcp-hosted`
- 1 task definition family named `followupboss-mcp-hosted`
- 1 CloudWatch log group
- 1 task execution role with `AmazonECSTaskExecutionRolePolicy`
- 1 task role with the inline policy derived from `task-role-policy.template.json`
- 1 ALB listener on `443`
- 1 Route53 alias record for the shared MCP hostname

## Reference Build And Push Commands

Create the ECR repository once:

```bash
aws ecr create-repository \
  --repository-name followupboss-mcp-hosted \
  --region __AWS_REGION__
```

Authenticate Docker against ECR:

```bash
aws ecr get-login-password --region __AWS_REGION__ | docker login \
  --username AWS \
  --password-stdin __AWS_ACCOUNT_ID__.dkr.ecr.__AWS_REGION__.amazonaws.com
```

Build and push the hosted image as a multi-architecture manifest so default ECS/Fargate runtimes
can pull it on either `linux/amd64` or `linux/arm64`:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag __AWS_ACCOUNT_ID__.dkr.ecr.__AWS_REGION__.amazonaws.com/followupboss-mcp-hosted:production \
  --push .
```

## Secrets Layout

Store non-tenant runtime connection URLs separately from tenant credentials:

- one Secrets Manager secret whose secret string is the PostgreSQL connection URL used for
  `FOLLOWUPBOSS_TENANT_DATABASE_URL`
- one Secrets Manager secret whose secret string is the Redis URL used for
  `FOLLOWUPBOSS_REDIS_URL`
- one Secrets Manager secret whose secret string is the Follow Up Boss OAuth client secret
- one Secrets Manager secret whose secret string is the Follow Up Boss registered-system key used
  for OAuth-created tenant credentials
- one Secrets Manager prefix for tenant Follow Up Boss credentials scoped to the deployed MCP URL

Do not place raw tenant Follow Up Boss API keys, OAuth access tokens, or `system_key` values in
the ECS task definition or any plaintext database column.

## Registering The Task Definition

After replacing all placeholders in `task-definition.template.json`, register it with:

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/ecs/task-definition.rendered.json \
  --region us-west-1
```

After replacing placeholders in `task-role-policy.template.json`, attach it to the ECS task role:

```bash
aws iam put-role-policy \
  --role-name followupboss-mcp-hosted-task-role \
  --policy-name FollowUpBossHostedTaskSecrets \
  --policy-document file://deploy/ecs/task-role-policy.rendered.json
```

## Post-Deploy Validation

Use the production validation commands in [`docs/hosted-deployment-guide.md`](../../docs/hosted-deployment-guide.md)
once the shared production MCP URL is live. Do not widen rollout until
[`docs/multi-tenant-hosting-checklist.md`](../../docs/multi-tenant-hosting-checklist.md) Phase 9
is completed with real evidence.

## GitHub Actions Production Deploy

The repository now includes `.github/workflows/deploy-production.yml` for automated production deploys.
It triggers on pushes to `main` and on manual dispatch, reruns `make release-validate`, builds and
pushes the hosted image to ECR, renders `deploy/ecs/task-definition.template.json`, registers a new
task definition revision, updates the ECS service, and waits for the service to become stable.

Configure a GitHub Actions environment named `production` with these repository or environment
variables:

- `AWS_REGION`
- `DEPLOYMENT_ENVIRONMENT` (optional; defaults to `production` in the workflow)
- `ECR_REPOSITORY`
- `ECS_CLUSTER`
- `ECS_SERVICE`
- `HOSTED_ISSUER_URL`
- `HOSTED_RESOURCE_SERVER_URL`
- `LOG_GROUP_NAME`
- `SENTRY_DSN` (optional; omit or leave empty to disable Sentry)
- `SENTRY_ENVIRONMENT` (optional; defaults to `production` in the production workflow)
- `SENTRY_TRACES_SAMPLE_RATE` (optional; leave empty to disable tracing)
- `TENANT_SECRET_PREFIX`
- `TENANT_SECRET_REGION`

The current production Sentry project is `theperrygroup/followupboss-mcp` in the US Sentry region.
Keep the project DSN in the GitHub `production` environment's `SENTRY_DSN` variable instead of
hardcoding it in this template.

The production workflow sets `SENTRY_RELEASE` to `followupboss-mcp@${{ github.sha }}` when rendering
the task definition. Its sanitized deployment receipt includes the exact registered task-definition
ARN. After authenticated modern and legacy live probes, use the workflow's `record-acceptance`
operation to bind separate sanitized-evidence digests to that ARN and Git SHA in an immutable
Actions artifact. Finalization accepts the successful callback run ID, not operator-supplied release
identifiers.

Restrict the `production` environment's deployment branch policy to `main`. The workflow also
rejects every other ref before a job can receive environment secrets. The OIDC deployment role must
allow the existing ECR image upload, task-definition registration, and service update actions plus
the metadata probe and migration runner's `ecs:DescribeServices`, `ecs:DescribeTaskDefinition`, `ecs:RunTask`,
`ecs:DescribeTasks`, and `logs:GetLogEvents` actions. Its `iam:PassRole` scope must
include the configured task and task execution roles used by the metadata probe and dedicated
migration task. Both one-shot definitions use the dedicated
`followupboss-mcp-oauth-resource-migration` task family so the role can keep one narrow
`ecs:RunTask` resource boundary. The metadata probe runs the current production image under the
existing task role,
requires the running task definition's image to be content-addressed by digest, requests only
`secretsmanager:DescribeSecret`, injects no secret values, and emits an allowlisted version-metadata
receipt. The workflow safely converts a proven bare reference once, then keeps the sole completed
ECS deployment, migration task, and new release on that authoritative immutable database-secret
version. Only explicit `expand` may perform the first pin and enable the deployment circuit breaker;
all other migration operations fail closed while the service remains bare and never update it. The
workflow conservatively proves that the current deployment postdates the secret version, rejects a
distinct `AWSPENDING` version, and requires unchanged version metadata after the first pin. It never
auto-advances an already-pinned service during secret rotation.

Set `FUB_OAUTH_ENABLED=true` only after configuring the hosted OAuth app. When OAuth is enabled,
also configure these variables:

- `FUB_OAUTH_CALLBACK_URL`
- `FUB_OAUTH_CLIENT_ID`
- `FUB_OAUTH_SYSTEM_NAME`

Configure the same `production` environment with these secrets:

- `AWS_ROLE_TO_ASSUME`
- `REDIS_URL_SECRET_ARN`
- `TENANT_DATABASE_URL_SECRET_ARN` (the canonical bare Secrets Manager ARN; do not append a version)
- `TASK_EXECUTION_ROLE_ARN`
- `TASK_ROLE_ARN`

When `FUB_OAUTH_ENABLED=true`, also configure these secrets:

- `FUB_OAUTH_CLIENT_SECRET_ARN`
- `FUB_OAUTH_SYSTEM_KEY_SECRET_ARN`

The repository also includes `.github/workflows/publish.yml` for PyPI releases. That workflow
triggers on `v*` tags, reruns `make release-validate`, verifies the tag matches
`pyproject.toml`'s package version, and publishes the package only after those checks pass.
