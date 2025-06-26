# ML Server Workflows

## Current Workflow Structure

### `release.yml` - Combined Build and Deploy Workflow ✅

- **Trigger**: `release-*` tags (e.g., `release-1.0.0`)
- **Jobs**:
  1. `build-and-push`: Builds and pushes Docker image to GHCR
  2. `deploy`: Deploys the built image to AWS using Ansible
- **Usage**: `git tag release-1.0.0 && git push origin release-1.0.0`

### `build.yml` - DEPRECATED ❌

- **Status**: Deprecated - shows error message and fails
- **Replacement**: Use `release-*` tags instead of `build-*` tags

### `new-ml-instance-created.yml` - Instance Setup

- **Purpose**: Sets up new ML server instances when they're created

## Migration Guide

**Before (Required 2 separate commands):**

```bash
# Step 1: Build
git tag build-1.0.0
git push origin build-1.0.0

# Step 2: Deploy (after build completes)
git tag release-1.0.0
git push origin release-1.0.0
```

**After (Single command):**

```bash
# Single step: Build + Deploy
git tag release-1.0.0
git push origin release-1.0.0
```

The release workflow now handles both building and deployment sequentially without requiring manual intervention between steps.
