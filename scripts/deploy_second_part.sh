#!/bin/bash
set -euo pipefail

PORT=22009
MACHINE="paffenroth-23.dyn.wpi.edu"
STUDENT_ADMIN_KEY_PATH="$HOME/.ssh/DSCS553_CASESTUDY2"
PRIVATE_KEY="$STUDENT_ADMIN_KEY_PATH/key1"

# HuggingFace token (use GitHub Secrets if automated)
# HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxx"

# Ensure the key exists
if [ ! -f "$PRIVATE_KEY" ]; then
    echo "❌ Error: Private key $PRIVATE_KEY not found"
    exit 1
fi

COMMAND="ssh -i $PRIVATE_KEY -p $PORT -o StrictHostKeyChecking=no student-admin@$MACHINE"

# Ensure repo exists on remote
$COMMAND "ls DSCS553_CASESTUDY1 || echo '❌ Repo missing!'"

# Install Python venv and dependencies
$COMMAND "sudo apt-get update -qq && sudo apt-get install -qq -y python3-venv python3-pip"

# Create virtual environment
$COMMAND "cd DSCS553_CASESTUDY1 && python3 -m venv venv"

# Activate venv and install requirements
$COMMAND "cd DSCS553_CASESTUDY1 && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Kill any old process before restart
$COMMAND "pkill -f DSCS553_CASESTUDY1/app.py || true"

# Start the app in background with HF_TOKEN
$COMMAND "nohup env HF_TOKEN=$HF_TOKEN DSCS553_CASESTUDY1/venv/bin/python3 DSCS553_CASESTUDY1/app.py > DSCS553_CASESTUDY1/log.txt 2>&1 &"

echo "✅ Deployment complete. App should now be running on $MACHINE:8009"

# Show last 20 lines of log for quick debugging
$COMMAND "tail -n 20 DSCS553_CASESTUDY1/log.txt || echo '⚠️ No logs yet'"
