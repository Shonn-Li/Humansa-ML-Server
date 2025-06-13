#!/bin/bash

set -e # Exit on any error

TAG="release-1.4.0"
BRANCH="main"
REPO_PATH=$(git config --get remote.origin.url | sed 's/.*github.com[:\/]\(.*\)\.git/\1/')
REPO_PATH=${REPO_PATH:-"shonn-li/youwoai-ml-server"} # Fallback

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "No GITHUB_TOKEN environment variable found."
    echo "Please set it to use the specific workflow URL feature:"
    echo "export GITHUB_TOKEN=your_personal_access_token"
    USE_API=false
else
    USE_API=true
fi

echo "🤖 YouWoAI ML Server One-Click Release Script"
echo "--------------------------------------------"
echo "This script will:"
echo "1. Automatically commit changes with message 'ml release script'"
echo "2. Delete tag $TAG locally and remotely"
echo "3. Recreate the tag at the current HEAD"
echo "4. Push the tag to trigger the ML server release workflow"
if [ "$USE_API" = true ]; then
    echo "5. Open the specific workflow run in your browser"
else
    echo "5. Open the GitHub Actions page in your browser"
fi
echo

# Check branch and switch if needed
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  echo "⚠️  Currently on branch $CURRENT_BRANCH, switching to $BRANCH..."
  git checkout $BRANCH
fi

# Pull latest changes
echo "📥 Pulling latest changes from origin/$BRANCH..."
git pull origin $BRANCH

# Commit if needed
if [ -n "$(git status --porcelain)" ]; then
  echo "📝 Uncommitted changes detected. Committing with message 'ml release script'..."
  git add .
  git commit -m "ml release script"
  
  echo "⬆️  Pushing changes to origin/$BRANCH..."
  git push origin $BRANCH
else
  echo "✅ No local changes to commit."
fi

# Delete tag
echo "🗑️  Deleting tag $TAG locally and remotely..."
git tag -d $TAG 2>/dev/null || true
git push origin :refs/tags/$TAG 2>/dev/null || true

# Create new tag
echo "🏷️  Creating new tag $TAG at current HEAD..."
git tag $TAG

# Push tag
echo "🚀 Pushing tag to trigger ML server release workflow..."
git push origin $TAG

# General Actions URL as fallback
ACTIONS_URL="https://github.com/$REPO_PATH/actions"

if [ "$USE_API" = true ]; then
    MAX_ATTEMPTS=12
    ATTEMPT=1
    FOUND=false
    
    echo "⏳ Waiting for workflow to start (checking every 5 seconds)..."
    
    # Function to check for the workflow run
    check_workflow() {
        # Get the latest workflow run for this tag
        API_URL="https://api.github.com/repos/$REPO_PATH/actions/runs?event=push&status=in_progress"
        RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$API_URL")
        
        # Check if there's a workflow run for our tag
        if echo "$RESPONSE" | grep -q "\"head_branch\":\"$TAG\""; then
            # Extract the run ID
            RUN_ID=$(echo "$RESPONSE" | grep -o "\"id\":[0-9]*" | head -1 | grep -o "[0-9]*")
            echo "✅ Found workflow run with ID: $RUN_ID"
            
            # Get the job details
            JOBS_URL="https://api.github.com/repos/$REPO_PATH/actions/runs/$RUN_ID/jobs"
            JOBS_RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$JOBS_URL")
            
            # Extract the first job ID (usually the deploy job)
            JOB_ID=$(echo "$JOBS_RESPONSE" | grep -o "\"id\":[0-9]*" | head -1 | grep -o "[0-9]*")
            
            if [ -n "$JOB_ID" ]; then
                echo "✅ Found job with ID: $JOB_ID"
                # Construct the job URL
                JOB_URL="https://github.com/$REPO_PATH/actions/runs/$RUN_ID/job/$JOB_ID"
                echo "🔗 Opening specific job: $JOB_URL"
                open "$JOB_URL"
                return 0
            else
                # Fallback to the workflow run URL
                WORKFLOW_URL="https://github.com/$REPO_PATH/actions/runs/$RUN_ID"
                echo "🔗 Opening workflow run: $WORKFLOW_URL"
                open "$WORKFLOW_URL"
                return 0
            fi
        fi
        return 1
    }
    
    # Loop to check for workflow
    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        echo "🔍 Checking for workflow run (attempt $ATTEMPT/$MAX_ATTEMPTS)..."
        if check_workflow; then
            FOUND=true
            break
        fi
        ATTEMPT=$((ATTEMPT+1))
        sleep 5
    done
    
    if [ "$FOUND" = false ]; then
        echo "⚠️ Could not find specific workflow run after 60 seconds."
        echo "👉 Opening general Actions page..."
        open "$ACTIONS_URL"
    fi
else
    echo "👉 Opening GitHub Actions page..."
    open "$ACTIONS_URL"
fi

echo "✅ Your ML server tag has been pushed and the deployment workflow is running."
