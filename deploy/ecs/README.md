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
| `__AWS_REGION__` | AWS region, such as `us-west-1`. |
| `__HOSTED_ISSUER_URL__` | Stable issuer URL for hosted auth, such as the customer portal or control plane. |
| `__HOSTED_RESOURCE_SERVER_URL__` | External HTTPS MCP URL, such as `https://mcp-staging.example.com/mcp`. |
| `__IMAGE_URI__` | Full ECR image URI, including tag. |
| `__LOG_GROUP_NAME__` | CloudWatch Logs group name for the ECS service. |
| `__REDIS_URL_SECRET_ARN__` | Secrets Manager ARN whose secret string is the complete Redis URL. |
| `__TASK_EXECUTION_ROLE_ARN__` | ECS task execution role ARN. |
| `__TASK_ROLE_ARN__` | ECS task role ARN used by the app at runtime. |
| `__TENANT_DATABASE_URL_SECRET_ARN__` | Secrets Manager ARN whose secret string is the complete PostgreSQL connection URL. |
| `__TENANT_SECRET_PREFIX__` | Tenant secret prefix, such as `followupboss/staging/tenants/`. |
| `__TENANT_SECRET_PREFIX_ARN__` | Secrets Manager ARN prefix, such as `arn:aws:secretsmanager:us-west-1:123456789012:secret:followupboss/staging/tenants/`. |
| `__TENANT_SECRET_REGION__` | AWS region for the tenant secret store. |

## Reference ECS Runtime Shape

Use one public Application Load Balancer plus one ECS/Fargate service in the default VPC or an
equivalent trusted VPC. The container should listen on port `8000`, and the ALB should forward
HTTPS traffic for `/mcp` to the task target group over HTTP.

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
  --region us-west-1
```

Authenticate Docker against ECR:

```bash
aws ecr get-login-password --region us-west-1 | docker login \
  --username AWS \
  --password-stdin 581917479192.dkr.ecr.us-west-1.amazonaws.com
```

Build and push the hosted image:

```bash
docker build \
  -t 581917479192.dkr.ecr.us-west-1.amazonaws.com/followupboss-mcp-hosted:staging .

docker push \
  581917479192.dkr.ecr.us-west-1.amazonaws.com/followupboss-mcp-hosted:staging
```

## Secrets Layout

Store non-tenant runtime connection URLs separately from tenant credentials:

- one Secrets Manager secret whose secret string is the PostgreSQL connection URL used for
  `FOLLOWUPBOSS_TENANT_DATABASE_URL`
- one Secrets Manager secret whose secret string is the Redis URL used for
  `FOLLOWUPBOSS_REDIS_URL`
- one Secrets Manager prefix for tenant Follow Up Boss credentials, such as
  `followupboss/staging/tenants/tenant-a/...`

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

Use the staged validation commands in [`docs/hosted-deployment-guide.md`](../../docs/hosted-deployment-guide.md)
once the shared staging URL is live. Do not widen rollout until
[`docs/multi-tenant-hosting-checklist.md`](../../docs/multi-tenant-hosting-checklist.md) Phase 9
is completed with real evidence.
