# AWS Lightsail Demo Deployment Guide

AWS Lightsail is the simplest way to host the SES Dispatch app on AWS.
It's a managed VPS with fixed monthly pricing — no surprise bills, no
complex security groups, and a browser-based SSH terminal so you don't
need to manage `.pem` key files.

---

## Prerequisites

- An AWS account ([create one here](https://aws.amazon.com/free/))
- No other tools required — everything is done in the browser

---

## Step 1: Create a Lightsail Instance

1. Go to [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Click **Create instance**
3. Configure:
   - **Region**: Asia Pacific (Sydney) — `ap-southeast-2`
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only > **Ubuntu 22.04 LTS**
   - **Instance plan**:
     - **$5 USD/month** (1 GB RAM, 1 vCPU, 40 GB SSD) — recommended
     - $3.50 USD/month (512 MB RAM) — works but tight
     - First 3 months are free on the $5 plan or below
   - **Instance name**: `ses-dispatch-demo`
4. Click **Create instance**

The instance takes about 30 seconds to launch.

---

## Step 2: Configure Networking

1. On the instance page, click the **Networking** tab
2. Under **IPv4 Firewall**, confirm these rules exist (they should by default):
   - SSH (port 22)
   - HTTP (port 80)
3. Click **Add rule** to add:
   - **HTTPS (port 443)** — needed if you add a domain later
4. (Optional) Click **Create static IP** to prevent the IP changing on reboot
   - Static IPs are free while attached to a running instance
   - Give it a name like `ses-dispatch-ip`
   - Note the IP address — this is your demo URL

---

## Step 3: Connect to Your Instance

### Option A: Browser terminal (easiest — no keys needed)

1. On the Lightsail instance page, click the orange **Connect using SSH** button
2. A terminal opens in your browser — you're logged in as `ubuntu`

### Option B: SSH from your local terminal

1. On the instance page, go to the **Connect** tab
2. Download the default SSH key
3. Connect:
   ```bash
   chmod 400 LightsailDefaultKey-ap-southeast-2.pem
   ssh -i LightsailDefaultKey-ap-southeast-2.pem ubuntu@<static-ip>
   ```

### Option C: VS Code Remote-SSH

1. Install the "Remote - SSH" extension in VS Code
2. Press `Ctrl+Shift+P` > "Remote-SSH: Connect to Host"
3. Enter: `ubuntu@<static-ip>`
4. Select the Lightsail SSH key when prompted
5. You can now edit files on the server directly in VS Code

---

## Step 4: Upload and Deploy

### Option A: Upload from your local machine then deploy

From your local terminal (not the Lightsail terminal):

```bash
# Upload the project files to the server
scp -i LightsailDefaultKey-ap-southeast-2.pem \
    -r ses_dispatch/ \
    ubuntu@<static-ip>:/tmp/ses_dispatch/
```

Then in the Lightsail terminal (browser SSH or local SSH):

```bash
# Move files into place
sudo mkdir -p /opt/ses-dispatch
sudo chown ubuntu:ubuntu /opt/ses-dispatch
mv /tmp/ses_dispatch /opt/ses-dispatch/ses_dispatch

# Run the deployment script
cd /opt/ses-dispatch/ses_dispatch
bash deploy/ec2_setup.sh
```

### Option B: Deploy from a Git repo

In the Lightsail terminal:

```bash
REPO_URL=https://github.com/your-org/ses-dispatch.git \
bash <(curl -sL https://raw.githubusercontent.com/your-org/ses-dispatch/main/ses_dispatch/deploy/ec2_setup.sh)
```

### Option C: Paste files via the browser terminal

If you only need to update a few files, you can paste content directly
into the browser terminal using `nano` or `cat >`:

```bash
nano /opt/ses-dispatch/ses_dispatch/dispatch/models.py
# Paste content, Ctrl+O to save, Ctrl+X to exit
```

---

## Step 5: Access the App

- **URL**: `http://<your-lightsail-ip>`
- **Login**: `admin` / `ses-demo-2026`
- **Admin panel**: `http://<your-lightsail-ip>/admin/`

### What you'll see

- **ICP Dashboard** — job queue, crew status, map, dispatch recommendations
- **Crew Screen** — mobile view at `/crew-screen/`
- **Photo Upload** — test by clicking "Send Upload Link" on a job, then
  opening the logged URL

---

## Step 6: (Optional) Add a Custom Domain with HTTPS

If you have a domain name:

1. Point your domain's **A record** to the Lightsail static IP:
   - `dispatch.yourunit.vic.ses.org.au` → `<static-ip>`
   - DNS propagation takes 5–30 minutes

2. Re-run the setup script with the domain:
   ```bash
   cd /opt/ses-dispatch/ses_dispatch
   DOMAIN=dispatch.yourunit.vic.ses.org.au bash deploy/ec2_setup.sh
   ```
   Caddy will automatically obtain a Let's Encrypt SSL certificate.

3. Access at: `https://dispatch.yourunit.vic.ses.org.au`

---

## Daily Operations

```bash
# Check app status
sudo systemctl status ses-dispatch

# View live logs
sudo journalctl -u ses-dispatch -f

# View Django application logs
cat /opt/ses-dispatch/ses_dispatch/logs/django.log

# Restart the app (after code changes)
sudo systemctl restart ses-dispatch

# Reset demo data (clears all data, reloads 4 crews + 8 jobs)
cd /opt/ses-dispatch/ses_dispatch
source .venv/bin/activate
python manage.py flush --no-input
python manage.py loaddata data/fixtures/demo_data.json
sudo systemctl restart ses-dispatch
```

---

## Updating the App

After making local changes:

```bash
# From your local machine — upload changed files
rsync -avz -e "ssh -i LightsailDefaultKey-ap-southeast-2.pem" \
    --exclude='.venv' --exclude='__pycache__' --exclude='db.sqlite3' \
    --exclude='media' --exclude='staticfiles' --exclude='logs' \
    ses_dispatch/ ubuntu@<static-ip>:/opt/ses-dispatch/ses_dispatch/

# Then SSH in and restart
ssh -i LightsailDefaultKey-ap-southeast-2.pem ubuntu@<static-ip>
cd /opt/ses-dispatch/ses_dispatch
source .venv/bin/activate
python manage.py migrate --no-input
python manage.py collectstatic --no-input
sudo systemctl restart ses-dispatch
```

Or if using Git:

```bash
# On the server
cd /opt/ses-dispatch
git pull
cd ses_dispatch
source .venv/bin/activate
python manage.py migrate --no-input
python manage.py collectstatic --no-input
sudo systemctl restart ses-dispatch
```

---

## Cost

| Component | First 3 months | After |
|-----------|---------------|-------|
| Lightsail 1GB instance | **Free** | $5 USD (~$8 AUD)/month |
| Static IP (attached) | Free | Free |
| 40 GB SSD storage | Included | Included |
| 2 TB data transfer | Included | Included |
| SSL certificate | Free (Caddy) | Free |
| **Total** | **$0** | **~$8 AUD/month** |

This is the cheapest always-on AWS option. No hidden charges — the
monthly price is fixed regardless of traffic.

---

## Stopping Costs

```bash
# Stop the instance (no charges while stopped)
# Go to Lightsail Console > select instance > Stop

# Or via CLI:
aws lightsail stop-instance --instance-name ses-dispatch-demo

# Start again when needed:
aws lightsail start-instance --instance-name ses-dispatch-demo
```

To fully delete (stop all charges):

```bash
aws lightsail delete-instance --instance-name ses-dispatch-demo
```

Or just click **Delete** on the Lightsail console.

---

## Lightsail vs EC2 — Why Lightsail for Demos

| Factor | Lightsail | EC2 |
|--------|-----------|-----|
| Setup | 2 minutes, all in browser | 5+ minutes, security groups, key pairs |
| SSH | Browser terminal built in | Need `.pem` file |
| Pricing | Fixed $5/month | Variable (free tier 12 months, then ~$13/month) |
| Static IP | Free (while attached) | $3.60/month (Elastic IP) |
| Firewall | Simple toggle UI | Security group rules |
| Storage | 40 GB included | 8 GB default (pay for more) |
| Data transfer | 2 TB included | Pay per GB after 1 GB |
| Best for | Demos, small apps | Production, auto-scaling |

---

## Troubleshooting

### App not loading

```bash
# Check if gunicorn is running
sudo systemctl status ses-dispatch

# Check if Caddy is running
sudo systemctl status caddy

# Check gunicorn logs
sudo journalctl -u ses-dispatch --no-pager -n 50

# Check Caddy logs
sudo journalctl -u caddy --no-pager -n 50
```

### SpatiaLite errors

```bash
# Verify SpatiaLite is installed
python3 -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.enable_load_extension(True); conn.load_extension('mod_spatialite')"

# If it fails, reinstall:
sudo apt install libsqlite3-mod-spatialite
```

### Permission errors

```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /opt/ses-dispatch
```

### Reset everything from scratch

```bash
cd /opt/ses-dispatch/ses_dispatch
source .venv/bin/activate
rm db.sqlite3
python manage.py migrate --no-input
python manage.py loaddata data/fixtures/demo_data.json
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'ses-demo-2026')"
sudo systemctl restart ses-dispatch
```
