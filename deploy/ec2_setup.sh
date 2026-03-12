#!/usr/bin/env bash
# =============================================================================
# SES Dispatch — EC2 Demo Deployment Script
# =============================================================================
#
# Deploys the Django app on a fresh Ubuntu 22.04/24.04 EC2 instance using:
#   - SQLite + SpatiaLite (no external database)
#   - Gunicorn (application server, systemd service)
#   - Caddy (reverse proxy, automatic HTTPS if domain provided)
#   - Local filesystem for photo uploads
#
# PREREQUISITES:
#   1. Launch an EC2 t2.micro (free tier) with Ubuntu 22.04 or 24.04 AMI
#   2. Security group: allow inbound TCP 22, 80, 443
#   3. SSH in: ssh -i your-key.pem ubuntu@<public-ip>
#
# USAGE:
#   # Without a domain (HTTP only, access via IP):
#   curl -sL <raw-script-url> | bash
#   # — or clone the repo first, then: —
#   bash deploy/ec2_setup.sh
#
#   # With a domain (automatic HTTPS via Let's Encrypt):
#   DOMAIN=dispatch.example.com bash deploy/ec2_setup.sh
#
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
APP_DIR="/opt/ses-dispatch/ses_dispatch"
REPO_DIR="/opt/ses-dispatch"
DOMAIN="${DOMAIN:-}"              # Set to your domain for HTTPS, or leave empty
DEMO_USER="${DEMO_USER:-admin}"
DEMO_PASS="${DEMO_PASS:-ses-demo-2026}"
DEMO_EMAIL="${DEMO_EMAIL:-admin@example.com}"
BRANCH="${BRANCH:-main}"
REPO_URL="${REPO_URL:-}"          # Set if deploying from a git repo

echo "============================================="
echo "  SES Dispatch — EC2 Demo Setup"
echo "============================================="
echo ""

# --- 1. System packages ------------------------------------------------------
echo "[1/8] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    libsqlite3-mod-spatialite \
    libgdal-dev libgeos-dev libproj-dev \
    gdal-bin \
    curl \
    git

# --- 2. Install Caddy --------------------------------------------------------
echo "[2/8] Installing Caddy..."
if ! command -v caddy &> /dev/null; then
    sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
        sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
        sudo tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq caddy
fi

# --- 3. Deploy application code ----------------------------------------------
echo "[3/8] Deploying application code..."
sudo mkdir -p "$REPO_DIR"
sudo chown ubuntu:ubuntu "$REPO_DIR"

if [ -n "$REPO_URL" ]; then
    # Clone from git
    if [ -d "$REPO_DIR/.git" ]; then
        cd "$REPO_DIR" && git pull origin "$BRANCH"
    else
        git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    fi
elif [ -f "manage.py" ]; then
    # Running from inside the repo — copy files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"
    if [ "$SOURCE_DIR" != "$APP_DIR" ]; then
        rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='db.sqlite3' \
            --exclude='media' --exclude='staticfiles' --exclude='logs' \
            "$SOURCE_DIR/" "$APP_DIR/"
    fi
elif [ -d "../ses_dispatch" ]; then
    # Running from deploy/ directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"
    rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='db.sqlite3' \
        --exclude='media' --exclude='staticfiles' --exclude='logs' \
        "$SOURCE_DIR/" "$APP_DIR/"
else
    echo "ERROR: Cannot find application code."
    echo "Either set REPO_URL, or run this script from the ses_dispatch directory."
    exit 1
fi

# --- 4. Python virtual environment -------------------------------------------
echo "[4/8] Setting up Python environment..."
cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet gunicorn whitenoise

# --- 5. Create directories and environment file -------------------------------
echo "[5/8] Configuring application..."
mkdir -p logs media

# Generate a random secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

# Determine allowed hosts
if [ -n "$DOMAIN" ]; then
    ALLOWED_HOSTS="$DOMAIN"
else
    # Get the EC2 public IP
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
    if [ -z "$PUBLIC_IP" ]; then
        # Fallback: try to get IP from hostname
        PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "*")
    fi
    ALLOWED_HOSTS="$PUBLIC_IP,localhost,127.0.0.1"
fi

cat > .env << ENVFILE
DJANGO_SETTINGS_MODULE=config.settings.demo
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=${ALLOWED_HOSTS}
ENVFILE

# --- 6. Django setup (migrate, static, fixtures, superuser) ------------------
echo "[6/8] Running Django setup..."
export DJANGO_SETTINGS_MODULE=config.settings.demo
export SECRET_KEY="$SECRET_KEY"
export ALLOWED_HOSTS="$ALLOWED_HOSTS"

python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py loaddata data/fixtures/demo_data.json || true

# Create demo superuser
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='${DEMO_USER}').exists():
    User.objects.create_superuser('${DEMO_USER}', '${DEMO_EMAIL}', '${DEMO_PASS}')
    print('Created superuser: ${DEMO_USER}')
else:
    print('Superuser ${DEMO_USER} already exists')
"

# --- 7. Gunicorn systemd service ----------------------------------------------
echo "[7/8] Setting up Gunicorn service..."
sudo cp deploy/gunicorn.service /etc/systemd/system/ses-dispatch.service
sudo systemctl daemon-reload
sudo systemctl enable ses-dispatch
sudo systemctl restart ses-dispatch

# Wait for gunicorn to start
sleep 2
if sudo systemctl is-active --quiet ses-dispatch; then
    echo "  Gunicorn started successfully."
else
    echo "  WARNING: Gunicorn may not have started. Check: sudo journalctl -u ses-dispatch"
fi

# --- 8. Caddy reverse proxy ---------------------------------------------------
echo "[8/8] Configuring Caddy..."

if [ -n "$DOMAIN" ]; then
    # With domain: automatic HTTPS via Let's Encrypt
    sudo tee /etc/caddy/Caddyfile > /dev/null << CADDYEOF
${DOMAIN} {
    reverse_proxy 127.0.0.1:8000

    # Serve uploaded media files directly
    handle_path /media/* {
        root * ${APP_DIR}/media
        file_server
    }
}
CADDYEOF
else
    # No domain: HTTP only on port 80
    sudo tee /etc/caddy/Caddyfile > /dev/null << CADDYEOF
:80 {
    reverse_proxy 127.0.0.1:8000

    # Serve uploaded media files directly
    handle_path /media/* {
        root * ${APP_DIR}/media
        file_server
    }
}
CADDYEOF
fi

sudo systemctl restart caddy

# --- Done! --------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Deployment complete!"
echo "============================================="
echo ""
if [ -n "$DOMAIN" ]; then
    echo "  URL:       https://${DOMAIN}"
else
    echo "  URL:       http://${ALLOWED_HOSTS%%,*}"
fi
echo ""
echo "  Login:     ${DEMO_USER} / ${DEMO_PASS}"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status ses-dispatch    # App status"
echo "    sudo systemctl restart ses-dispatch   # Restart app"
echo "    sudo journalctl -u ses-dispatch -f    # App logs"
echo "    sudo systemctl status caddy           # Web server status"
echo "    cat ${APP_DIR}/logs/django.log        # Django logs"
echo ""
echo "  To update the app:"
echo "    cd ${APP_DIR}"
echo "    source .venv/bin/activate"
echo "    git pull  # (if using git)"
echo "    python manage.py migrate"
echo "    python manage.py collectstatic --no-input"
echo "    sudo systemctl restart ses-dispatch"
echo ""
echo "  To reset demo data:"
echo "    cd ${APP_DIR} && source .venv/bin/activate"
echo "    python manage.py flush --no-input"
echo "    python manage.py loaddata data/fixtures/demo_data.json"
echo "    sudo systemctl restart ses-dispatch"
echo "============================================="
