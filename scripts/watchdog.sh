set -euo pipefail

# ========= CONFIG =========
PORT=22009
MACHINE="paffenroth-23.dyn.wpi.edu"
USER="student-admin"
KEY_PATH="$HOME/.ssh/DSCS553_CASESTUDY2/key1"   # key to login CHANGE TO UR KEY!
DEPLOY_SCRIPT="$HOME/deploy.sh"                 # path to your deploy script
SEARCH_TERM="rcpaffenroth@paffenroth-23"
INTERVAL=600   # 600 seconds = 10 minutes
# ==========================

while true; do
    echo "⏳ Checking authorized_keys on $MACHINE ..."

    # Fetch authorized_keys content
    if ssh -i "$KEY_PATH" -p "$PORT" -o StrictHostKeyChecking=no \
        "$USER@$MACHINE" "grep -q '$SEARCH_TERM' ~/.ssh/authorized_keys"; then
        
        echo "⚠️  Bootstrap key still present! Running deploy.sh ..."
        bash "$DEPLOY_SCRIPT"
    else
        echo "✅ No bootstrap key found. System already configured."
    fi

    echo "Sleeping for $INTERVAL seconds..."
    sleep $INTERVAL
done

# run:  "nohup bash watchdog.sh > watchdog.log 2>&1 &" to run in background the script