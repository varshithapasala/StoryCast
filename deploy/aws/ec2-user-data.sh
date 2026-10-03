#!/bin/bash
set -euxo pipefail

dnf update -y
dnf install -y docker git curl
systemctl enable --now docker
usermod -aG docker ec2-user

mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

systemctl enable --now amazon-ssm-agent || true
mkdir -p /opt/storycast
chown ec2-user:ec2-user /opt/storycast
