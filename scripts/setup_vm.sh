#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 22.04/24.04 VM. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/rmohanty521/vol-trading-system/main/scripts/setup_vm.sh | bash
# Then copy your .env to /opt/vol-trading-system/.env and run:
#   cd /opt/vol-trading-system && docker compose up -d --build
set -euo pipefail

REPO=https://github.com/rmohanty521/vol-trading-system.git
DIR=/opt/vol-trading-system

# Docker engine + compose plugin
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

# 2 GB swap: model training spikes memory on small VMs
if ! swapon --show | grep -q /swapfile; then
    fallocate -l 2G /swapfile && chmod 600 /swapfile
    mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# keep the clock right: the scheduler fires at 15:45 New York time
timedatectl set-ntp true || true

if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull --ff-only
else
    git clone "$REPO" "$DIR"
fi

echo
echo "done. next:"
echo "  1. copy your .env to $DIR/.env"
echo "  2. cd $DIR && docker compose up -d --build"
