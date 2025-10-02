#!/bin/bash
set -euo pipefail

# ========== CONFIGURATION ==========
PORT=22009
MACHINE="paffenroth-23.dyn.wpi.edu"

# Directory holding private/public keys (key1, key2, …, student-admin_key, etc.)
STUDENT_ADMIN_KEY_PATH="$HOME/.ssh/DSCS553_CASESTUDY2"

REPO_URL="https://github.com/SHADOW12021/DSCS553_CASESTUDY1.git"
REPO_DIR="DSCS553_CASESTUDY1"
BRANCH_NAME="case_study_1_2025"
MAIN_SCRIPT="app.py"
HF_TOKEN="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"
# ====================================

echo "📌 Adding all provided public keys to authorized_keys..."

cd "$STUDENT_ADMIN_KEY_PATH"

# Ensure permissions are sane
chmod 600 student-admin_key || true
chmod 600 key* || true
chmod 644 key*.pub || true

# Add all public keys using the bootstrap key
for PUBKEY in key*.pub; do
    echo "➡️ Adding $PUBKEY to server..."
    ssh -i "$STUDENT_ADMIN_KEY_PATH/student-admin_key" -p "$PORT" -o StrictHostKeyChecking=no \
        student-admin@"$MACHINE" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys" < "$PUBKEY"
done

echo "✅ All permanent keys added"

# 🔑 Test connection with key1 before removing bootstrap key
ssh -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "echo 'Logged in with key1 successfully'"

# 🚫 Now that key1 works, remove the bootstrap key from server
ssh -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
    student-admin@"$MACHINE" "sed -i '/rcpaffenroth@paffenroth-23/d' /home/student-admin/.ssh/authorized_keys && chmod 600 /home/student-admin/.ssh/authorized_keys"

echo "✅ Bootstrap key removed. Server is now secured with permanent keys only."

# === REMOTE SETUP, CLONE, INSTALL, AND LAUNCH ===
ssh -i "$STUDENT_ADMIN_KEY_PATH/key1" -p "$PORT" -o StrictHostKeyChecking=no \
  student-admin@"$MACHINE" bash <<ENDSSH
set -euo pipefail
REPO_DIR="\$HOME/$REPO_DIR"
MAIN_SCRIPT="$MAIN_SCRIPT"
PYTHON=python3.10
VENV_DIR="\$REPO_DIR/venv"
REQUIREMENTS_FILE="\$REPO_DIR/requirements.txt"
BRANCH_NAME="$BRANCH_NAME"
HF_TOKEN="$HF_TOKEN"

echo "Installing Python 3.10 if not present..."
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3.10-distutils python3.10-dev git

echo "Cloning repo from specified branch..."
rm -rf "\$REPO_DIR"
git clone --branch "\$BRANCH_NAME" --single-branch $REPO_URL "\$REPO_DIR"

echo "Setting up Python 3.10 virtual environment..."
\$PYTHON -m venv "\$VENV_DIR"
source "\$VENV_DIR/bin/activate"
\$PYTHON -m pip install --upgrade pip
\$PYTHON -m pip install -r "\$REQUIREMENTS_FILE"

echo "Killing any previous instance of app.py (if running)..."
pkill -f "\$MAIN_SCRIPT" || true

echo "Launching app.py in background—logs go to output.log"
nohup env HF_TOKEN="\$HF_TOKEN" \$PYTHON "\$REPO_DIR/\$MAIN_SCRIPT" > "\$REPO_DIR/output.log" 2>&1 &

echo "✅ Setup complete: repo ready and app running via nohup."
ENDSSH

echo "🎉 All steps finished! Your app is running in the background on the VM."
