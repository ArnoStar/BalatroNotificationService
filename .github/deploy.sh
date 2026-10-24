#!/usr/bin/env bash
# Deploys the notification service (GitHub Actions, deploy job): copies this checkout to the
# server, then rebuilds and restarts the notification service with BalatroFrontEnd's
# docker-compose.yml and waits until it is healthy. Until the front end has
# been deployed once (it brings the compose file), the code is only copied.
#
# The server keeps, in DEPLOY_PATH (/opt/balatro):
#   BalatroFrontEnd/   the front end and docker-compose.yml (its own deployment)
#   BalatroWebAPI/     the API (its own deployment)
#   BalatroIndentityService/  the identity service (its own deployment)
#   BalatroNotificationService/  this repository (copied here)
#   balatro_src/       a copy of the game, for the front end's image
#
# env: DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, DEPLOY_KNOWN_HOSTS,
#      DEPLOY_PORT (22), DEPLOY_PATH (/opt/balatro)
set -euo pipefail

: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_SSH_KEY:?}" "${DEPLOY_KNOWN_HOSTS:?}"
port="${DEPLOY_PORT:-22}"
root="${DEPLOY_PATH:-/opt/balatro}"
target="$DEPLOY_USER@$DEPLOY_HOST"

mkdir -p ~/.ssh
chmod 700 ~/.ssh
printf '%s\n' "$DEPLOY_SSH_KEY" > ~/.ssh/deploy_key
chmod 600 ~/.ssh/deploy_key
printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > ~/.ssh/deploy_known_hosts
ssh_cmd="ssh -i $HOME/.ssh/deploy_key -p $port -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/deploy_known_hosts"

$ssh_cmd "$target" "mkdir -p '$root/BalatroNotificationService'"
rsync -az --delete -e "$ssh_cmd" \
  --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  --exclude .mypy_cache --exclude .ruff_cache --exclude keys --exclude .env \
  ./ "$target:$root/BalatroNotificationService/"

$ssh_cmd "$target" bash -s -- "$root" <<'REMOTE'
set -euo pipefail
root="$1"
# one deployment at a time (the front end's deploys here too)
exec 9>"$root/.deploy.lock"
flock 9
cd "$root/BalatroFrontEnd" 2>/dev/null || true
if [ ! -f docker-compose.yml ] || ! docker compose config --services | grep -qx notification; then
  echo "::notice::The notification service's code is on the server; it starts with the next deployment of BalatroFrontEnd (whose docker-compose.yml runs it)"
  exit 0
fi
docker compose up -d --build notification
cid="$(docker compose ps -q notification)"
status=starting
for _ in $(seq 90); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$cid")"
  [ "$status" = healthy ] && break
  [ "$status" = unhealthy ] && break
  sleep 2
done
docker compose ps
if [ "$status" != healthy ]; then
  docker compose logs --tail 80 notification
  echo "::error::the notification service is $status"
  exit 1
fi
docker image prune -f > /dev/null
REMOTE
