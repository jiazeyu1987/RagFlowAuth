#!/usr/bin/env bash
set -euo pipefail

#
# setup-smb-replica.sh
#
# Mount a Windows SMB share on a Linux host and print the Docker bind-mount
# flags needed so the backend container can replicate backups to Windows.
#
# Usage examples:
#   sudo ./tool/scripts/setup-smb-replica.sh \
#     --windows-host 192.168.1.10 --share Backups \
#     --username backup_user --password '***' \
#     --mount-point /mnt/replica --persist
#

usage() {
  cat <<'EOF'
Mount Windows SMB share on Linux for RagflowAuth backup replication.

Required:
  --windows-host <ip|hostname>   Windows machine address
  --share <name>                 SMB share name (e.g. Backups)

Credentials (choose one):
  --creds-file <path>            Existing credentials file (chmod 600)
  --username <user> --password <pass> [--domain <dom>]

Options:
  --mount-point <path>           Default: /mnt/replica
  --vers <2.1|3.0|3.1.1>          Default: 3.0
  --uid <uid>                    Default: 1000
  --gid <gid>                    Default: 1000
  --install                       Attempt to install cifs-utils (apt/yum)
  --persist                       Add /etc/fstab entry for auto-mount
  --unmount                       Unmount and remove fstab entry for this mount
  --dry-run                       Print commands without executing

After success, bind-mount the host mount point into the backend container:
  -v /mnt/replica:/replica
Then set Data Security UI:
  replica_target_path=/replica/RagflowAuth
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }

WINDOWS_HOST=""
SHARE=""
MOUNT_POINT="/mnt/replica"
CREDS_FILE=""
USERNAME=""
PASSWORD=""
DOMAIN="WORKGROUP"
VERS="3.0"
UID_OPT="1000"
GID_OPT="1000"
DO_INSTALL="0"
DO_PERSIST="0"
DO_UNMOUNT="0"
DRY_RUN="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --windows-host) WINDOWS_HOST="${2:-}"; shift 2 ;;
    --share) SHARE="${2:-}"; shift 2 ;;
    --mount-point) MOUNT_POINT="${2:-}"; shift 2 ;;
    --creds-file) CREDS_FILE="${2:-}"; shift 2 ;;
    --username) USERNAME="${2:-}"; shift 2 ;;
    --password) PASSWORD="${2:-}"; shift 2 ;;
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --vers) VERS="${2:-}"; shift 2 ;;
    --uid) UID_OPT="${2:-}"; shift 2 ;;
    --gid) GID_OPT="${2:-}"; shift 2 ;;
    --install) DO_INSTALL="1"; shift ;;
    --persist) DO_PERSIST="1"; shift ;;
    --unmount) DO_UNMOUNT="1"; shift ;;
    --dry-run) DRY_RUN="1"; shift ;;
    *) die "Unknown argument: $1 (use --help)" ;;
  esac
done

[[ -n "$WINDOWS_HOST" ]] || die "Missing --windows-host"
[[ -n "$SHARE" ]] || die "Missing --share"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  die "Run as root (sudo) so we can mount and edit /etc/fstab"
fi

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "+ $*"
    return 0
  fi
  eval "$@"
}

ensure_cifs_utils() {
  if command -v mount.cifs >/dev/null 2>&1; then
    return 0
  fi
  [[ "$DO_INSTALL" == "1" ]] || die "mount.cifs not found. Install cifs-utils or run with --install"

  if command -v apt-get >/dev/null 2>&1; then
    run "apt-get update"
    run "apt-get install -y cifs-utils"
  elif command -v yum >/dev/null 2>&1; then
    run "yum install -y cifs-utils"
  else
    die "No supported package manager found (apt-get/yum). Install cifs-utils manually."
  fi
}

write_creds_file() {
  if [[ -n "$CREDS_FILE" ]]; then
    [[ -f "$CREDS_FILE" ]] || die "Credentials file not found: $CREDS_FILE"
    return 0
  fi

  [[ -n "$USERNAME" ]] || die "Missing --username (or provide --creds-file)"
  [[ -n "$PASSWORD" ]] || die "Missing --password (or provide --creds-file)"

  CREDS_FILE="/root/.smbcreds/ragflow_backup"
  run "mkdir -p \"$(dirname "$CREDS_FILE")\""

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "+ cat > \"$CREDS_FILE\" <<EOF"
    echo "username=$USERNAME"
    echo "password=***"
    echo "domain=$DOMAIN"
    echo "EOF"
  else
    cat >"$CREDS_FILE" <<EOF
username=$USERNAME
password=$PASSWORD
domain=$DOMAIN
EOF
    chmod 600 "$CREDS_FILE"
  fi
}

fstab_line() {
  # shellcheck disable=SC2001
  local host_share
  host_share="//${WINDOWS_HOST}/${SHARE}"
  echo "${host_share} ${MOUNT_POINT} cifs credentials=${CREDS_FILE},iocharset=utf8,uid=${UID_OPT},gid=${GID_OPT},file_mode=0660,dir_mode=0770,vers=${VERS},_netdev,nofail 0 0"
}

remove_fstab_entry() {
  local line_prefix="//${WINDOWS_HOST}/${SHARE} ${MOUNT_POINT} cifs "
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "+ (backup) remove matching /etc/fstab line: $line_prefix..."
    return 0
  fi
  if [[ -f /etc/fstab ]]; then
    cp -a /etc/fstab "/etc/fstab.bak.$(date +%s)"
    # Use fixed-string grep to filter out the exact mountpoint
    awk -v prefix="$line_prefix" 'index($0, prefix) != 1 { print }' /etc/fstab > /etc/fstab.tmp
    mv /etc/fstab.tmp /etc/fstab
  fi
}

add_fstab_entry_if_missing() {
  [[ "$DO_PERSIST" == "1" ]] || return 0
  local line
  line="$(fstab_line)"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "+ ensure /etc/fstab contains:"
    echo "$line"
    return 0
  fi
  if grep -Fq "$line" /etc/fstab; then
    return 0
  fi
  cp -a /etc/fstab "/etc/fstab.bak.$(date +%s)"
  echo "$line" >> /etc/fstab
}

do_mount() {
  local host_share="//${WINDOWS_HOST}/${SHARE}"
  run "mkdir -p \"$MOUNT_POINT\""

  # Avoid double-mounts.
  if mountpoint -q "$MOUNT_POINT"; then
    echo "Already mounted: $MOUNT_POINT"
    return 0
  fi

  local opts
  opts="credentials=${CREDS_FILE},iocharset=utf8,uid=${UID_OPT},gid=${GID_OPT},file_mode=0660,dir_mode=0770,vers=${VERS}"
  run "mount -t cifs \"$host_share\" \"$MOUNT_POINT\" -o \"$opts\""
}

verify_write() {
  local test_file="$MOUNT_POINT/.ragflowauth_replica_test_$$"
  run "touch \"$test_file\""
  run "rm -f \"$test_file\""
}

do_unmount() {
  if mountpoint -q "$MOUNT_POINT"; then
    run "umount \"$MOUNT_POINT\""
  fi
  remove_fstab_entry
}

main() {
  ensure_cifs_utils
  write_creds_file

  if [[ "$DO_UNMOUNT" == "1" ]]; then
    do_unmount
    echo "Unmounted: $MOUNT_POINT"
    exit 0
  fi

  do_mount
  verify_write
  add_fstab_entry_if_missing

  cat <<EOF

OK: SMB share mounted.
- Host mount point: $MOUNT_POINT
- Windows share: \\\\$WINDOWS_HOST\\$SHARE

Next:
1) Bind-mount into backend container:
   -v $MOUNT_POINT:/replica
2) In UI (Data Security):
   replica_enabled=true
   replica_target_path=/replica/RagflowAuth

Tip:
  If you use docker compose, add:
    volumes:
      - $MOUNT_POINT:/replica
EOF
}

main

