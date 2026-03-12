# EC2 Demo Deployment Guide

## Step 1: Launch EC2 Instance

1. Go to [AWS Console > EC2 > Launch Instance](https://console.aws.amazon.com/ec2/)
2. Configure:
   - **Name**: `ses-dispatch-demo`
   - **AMI**: Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance type**: `t2.micro` (free tier — 1 vCPU, 1GB RAM)
   - **Key pair**: Create or select an existing key pair (download the `.pem` file)
   - **Security group**: Create new with these inbound rules:
     - SSH (port 22) — your IP only
     - HTTP (port 80) — anywhere (0.0.0.0/0)
     - HTTPS (port 443) — anywhere (0.0.0.0/0)
   - **Storage**: 8 GB gp3 (default, free tier)
3. Click **Launch Instance**

## Step 2: Connect via SSH

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<ec2-public-ip>
```

## Step 3: Deploy

### Option A: From a Git repo (recommended)

```bash
REPO_URL=https://github.com/your-org/ses-dispatch.git \
bash <(curl -sL https://raw.githubusercontent.com/your-org/ses-dispatch/main/ses_dispatch/deploy/ec2_setup.sh)
```

### Option B: Upload files manually

```bash
# From your local machine:
scp -i your-key.pem -r ses_dispatch/ ubuntu@<ec2-ip>:/opt/ses-dispatch/ses_dispatch/

# Then SSH in and run:
ssh -i your-key.pem ubuntu@<ec2-ip>
cd /opt/ses-dispatch/ses_dispatch
bash deploy/ec2_setup.sh
```

### Option C: With a custom domain (HTTPS)

```bash
DOMAIN=dispatch.example.com \
REPO_URL=https://github.com/your-org/ses-dispatch.git \
bash deploy/ec2_setup.sh
```

Point your domain's DNS A record to the EC2 public IP first.

## Step 4: Access the App

- **URL**: `http://<ec2-public-ip>` (or `https://your-domain.com`)
- **Login**: `admin` / `ses-demo-2026`

## Daily Operations

```bash
# Check app status
sudo systemctl status ses-dispatch

# View logs
sudo journalctl -u ses-dispatch -f
cat /opt/ses-dispatch/ses_dispatch/logs/django.log

# Restart after code changes
sudo systemctl restart ses-dispatch

# Reset demo data (clears everything, reloads fixtures)
cd /opt/ses-dispatch/ses_dispatch
source .venv/bin/activate
python manage.py flush --no-input
python manage.py loaddata data/fixtures/demo_data.json
sudo systemctl restart ses-dispatch
```

## Cost

| Component | Free Tier (12 months) | After Free Tier |
|-----------|----------------------|-----------------|
| EC2 t2.micro | $0 | ~$12 AUD/month |
| 8 GB EBS storage | $0 | ~$1 AUD/month |
| Data transfer (demo) | $0 | ~$0 |
| **Total** | **$0** | **~$13 AUD/month** |

## Stopping Costs

To stop charges when not demoing:

```bash
# Stop the instance (no compute charges, EBS storage still charged ~$1/month)
aws ec2 stop-instances --instance-ids <instance-id>

# Start again when needed
aws ec2 start-instances --instance-ids <instance-id>
# Note: Public IP changes on restart unless you use an Elastic IP
```

To fully remove:
```bash
aws ec2 terminate-instances --instance-ids <instance-id>
```
