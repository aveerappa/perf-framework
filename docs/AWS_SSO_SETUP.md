# AWS SSO Setup for Performance Framework

The performance framework's `preflight.sh` requires AWS SSO authentication to access EKS clusters. This guide shows how to configure it for any computer.

## Quick Start

### Option 1: Use Standard Location (Easiest)

Create your AWS SSO script in one of these locations:

```bash
# Recommended location
mkdir -p ~/.aws
cp /path/to/your/aws-env.sh ~/.aws/aws-env.sh
```

or

```bash
# Alternative location
mkdir -p ~/.config/aws
cp /path/to/your/aws-env.sh ~/.config/aws/aws-env.sh
```

### Option 2: Custom Location with Environment Variable

If your AWS SSO script is in a custom location:

```bash
# Add to your ~/.zshrc or ~/.bashrc
export AWS_ENV_FILE="$HOME/your-custom-path/aws-env.sh"
```

Then reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

## How It Works

`preflight.sh` searches for your AWS SSO configuration in this order:

1. **Environment variable**: If `AWS_ENV_FILE` is set, use that path
2. **Standard locations** (checked in order):
   - `~/.aws/aws-env.sh`
   - `~/.config/aws/aws-env.sh`
   - `~/Documents/Work/workspace/aws-sso-setup/aws-env.sh` (legacy)

The first file found is used.

## Required Contents

Your `aws-env.sh` must define the `aws-qa-login` function that:

1. Authenticates with AWS SSO
2. Updates kubeconfig for your EKS cluster
3. Returns exit code 0 on success, non-zero on failure

**Example structure:**

```bash
#!/bin/bash

aws-qa-login() {
    # Authenticate with AWS SSO
    aws sso login --profile qa
    
    # Update kubeconfig
    aws eks update-kubeconfig \
        --region us-east-2 \
        --name bcas-qa-ue2-default-cluster \
        --profile qa
    
    return $?
}
```

## Verification

Test your setup:

```bash
# If using environment variable
echo $AWS_ENV_FILE

# Test the script exists
ls -l $AWS_ENV_FILE  # or ls -l ~/.aws/aws-env.sh

# Run preflight with any config
./preflight.sh projects/your-config.json
```

You should see:

```
2️⃣  Checking AWS QA SSO session...
   ✅ AWS qa profile active
```

## Troubleshooting

### Error: "aws-env.sh not found"

- Check the file exists in one of the standard locations
- Or set `AWS_ENV_FILE` environment variable
- Verify the path is correct: `ls -l "$AWS_ENV_FILE"`

### Error: "AWS qa SSO login failed"

- Check your `aws-env.sh` defines `aws-qa-login` function
- Test manually: `source ~/.aws/aws-env.sh && aws-qa-login`
- Verify AWS CLI is installed: `aws --version`
- Check SSO configuration: `aws sso login --profile qa`

## Different Team Setups

Each team may have different AWS SSO setups. Place your team-specific script in:

```bash
~/.aws/aws-env.sh  # Your personal setup
```

This keeps it separate from the framework code and works on any computer.
