# StoryCast on AWS EC2

This deployment runs the web app, API, PostgreSQL, Redis, Celery workers, and
Caddy on one EC2 instance. Generated videos are uploaded to a private S3 bucket.
Gemini and Hugging Face remain hosted inference providers.

It is intended for a portfolio/demo deployment. For a multi-user production
service, move PostgreSQL to RDS, Redis to ElastiCache, and containers to ECS.

## 1. Create the AWS resources

Use one AWS Region for all resources.

1. Create two private ECR repositories named `storycast-backend` and
   `storycast-frontend`.
2. Create a private S3 bucket with Block Public Access enabled.
3. Create an EC2 instance using Amazon Linux 2023:
   - `t3.large` is the recommended starting size.
   - Use at least 40 GB of encrypted gp3 storage.
   - Paste `ec2-user-data.sh` into the instance user-data field.
4. Attach an Elastic IP.
5. Allow inbound TCP 80 and 443 from the internet. Allow TCP 22 only from your
   own IP, or omit SSH and use Systems Manager Session Manager.
6. Attach an EC2 IAM role containing:
   - `AmazonSSMManagedInstanceCore`
   - the permissions in `ec2-instance-policy.json`, after replacing the bucket
     placeholder
7. Point the deployment domain's DNS A record to the Elastic IP.

Do not make the S3 bucket public. StoryCast returns short-lived presigned URLs
for downloads.

## 2. Bootstrap the instance

Connect through Session Manager or SSH, then clone the repository:

```bash
sudo git clone https://github.com/YOUR_OWNER/YOUR_REPOSITORY.git /opt/storycast
sudo chown -R ec2-user:ec2-user /opt/storycast
cd /opt/storycast
cp deploy/aws/.env.production.example .env.production
```

If the repository is private, configure a read-only deploy key before cloning.
The CI workflow runs `git pull --ff-only`, so the instance must retain read
access to the repository.

Generate the Caddy password hash:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'YOUR_DEMO_PASSWORD'
```

Edit `.env.production` and set:

- `APP_DOMAIN` and `ACME_EMAIL`
- `BASIC_AUTH_USERNAME` and the generated password hash
- one identical value for `POSTGRES_PASSWORD` and the password inside
  `DATABASE_URL`
- `GEMINI_API_KEY` and `HF_TOKEN`
- `AWS_REGION` and `S3_BUCKET`
- `CORS_ORIGINS=https://YOUR_DOMAIN`

Keep the password hash in single quotes because bcrypt hashes contain dollar
signs. Leave the S3 access-key values empty; boto3 will use the EC2 IAM role.

Start the first deployment from source:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f caddy api
```

Caddy obtains and renews the TLS certificate automatically after DNS and ports
80/443 are correct. Only Caddy publishes host ports; PostgreSQL, Redis, the API,
and the frontend remain on the private Compose network.

## 3. Configure GitHub Actions deployment

Create the GitHub Actions OIDC provider in AWS IAM if the account does not
already have one. Create a deployment role using
`github-oidc-trust-policy.json`, replacing every placeholder. Attach
`github-deploy-policy.json`, also replacing its placeholders.

In the GitHub repository's **Settings → Secrets and variables → Actions →
Variables**, create:

| Variable | Example |
| --- | --- |
| `AWS_REGION` | `ap-south-1` |
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::123456789012:role/storycast-github-deploy` |
| `ECR_BACKEND_REPOSITORY` | `storycast-backend` |
| `ECR_FRONTEND_REPOSITORY` | `storycast-frontend` |
| `EC2_INSTANCE_ID` | `i-0123456789abcdef0` |
| `DEPLOY_DIRECTORY` | `/opt/storycast` |

Protect the GitHub `production` environment with a required reviewer if desired.
The workflow uses OIDC, so no permanent AWS access keys are stored in GitHub.
It runs tests, builds both images, pushes commit-tagged images to ECR, and uses
Systems Manager Run Command to update EC2.

The workflow is skipped until all six variables exist. After configuration,
push to `main` or run **Deploy to AWS** manually.

## 4. Operations

Check application health:

```bash
curl -u reviewer:YOUR_DEMO_PASSWORD https://YOUR_DOMAIN/health
```

Inspect services and logs:

```bash
cd /opt/storycast
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=200 api worker-rendering
```

Back up the PostgreSQL volume regularly and configure an AWS Budget alert.
Hugging Face video generation and Gemini usage are billed separately from AWS.

## Security scope

Caddy Basic Authentication protects the complete portfolio deployment over
HTTPS and prevents anonymous visitors from spending AI credits. It is suitable
for a private recruiter demo with a shared credential. Replace it with real
application authentication and per-user authorization before offering a public
multi-user service.
