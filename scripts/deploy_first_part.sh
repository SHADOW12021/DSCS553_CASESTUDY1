#!/bin/bash
set -euo pipefail

PORT=22009
MACHINE="paffenroth-23.dyn.wpi.edu"
STUDENT_ADMIN_KEY_PATH="keys"

TMPDIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

# Ensure .ssh and known_hosts exist
mkdir -p ~/.ssh
touch ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts

# Optional: remove old entry for this host
ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$MACHINE" || true

# Copy pre-generated public keys into TMPDIR (optional)
cp "$STUDENT_ADMIN_KEY_PATH"/key*.pub "$TMPDIR"
chmod 700 "$TMPDIR"

# Ensure correct permissions for private key and public keys
chmod 600 "$STUDENT_ADMIN_KEY_PATH/key1"
chmod 644 "$STUDENT_ADMIN_KEY_PATH"/key*.pub

cd "$TMPDIR"

# Append all pre-generated public keys to server's authorized_keys
for PUBKEY in key*.pub; do
    ssh -i "$STUDENT_ADMIN_KEY_PATH/student-admin_key" -p "$PORT" -o StrictHostKeyChecking=no \
        student-admin@"$MACHINE" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys" < "$PUBKEY"
done

# Remove the bootstrap key from server
ssh -i "$STUDENT_ADMIN_KEY_PATH/student-admin_key" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "sed -i '/student-admin_key/d' ~/.ssh/authorized_keys"

# Fix permissions
ssh -i "$STUDENT_ADMIN_KEY_PATH/student-admin_key" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "chmod 600 ~/.ssh/authorized_keys"

echo "✅ All pre-generated keys added and bootstrap key removed"

# Test connection with key1 only
ssh -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "echo 'Logged in with key1'"

# Set root password interactively
echo "Please enter a new root password for the server:"
ssh -t -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" sudo passwd root


# Show final authorized_keys
echo "Final authorized_keys on server:"
ssh -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "cat ~/.ssh/authorized_keys"

# Clone repo locally and copy to server
git clone --branch case_study_1_2025 --single-branch https://github.com/SHADOW12021/DSCS553_CASESTUDY1.git
scp -i "$STUDENT_ADMIN_KEY_PATH/key1" -P "$PORT" -o StrictHostKeyChecking=no -r DSCS553_CASESTUDY1 \
    student-admin@"$MACHINE":~/

echo "Setup phase complete. Use the second script to finish install/startup."
