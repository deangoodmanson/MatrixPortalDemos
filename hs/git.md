# Git Setup Checklist for LED Portal

This guide walks you through putting the LED Portal project into a **private GitHub repository**. It's designed as a learning experience, explaining not just *what* to do, but *why*.

---

## Table of Contents

1. [Understanding Git and GitHub](#understanding-git-and-github)
2. [Tools You'll Need](#tools-youll-need)
3. [Installing the Tools](#installing-the-tools)
4. [Initial Git Configuration](#initial-git-configuration)
5. [Preparing Your Project](#preparing-your-project)
6. [Creating the Repository](#creating-the-repository)
7. [Your First Commit](#your-first-commit)
8. [Pushing to GitHub](#pushing-to-github)
9. [GitHub Security Settings](#github-security-settings)
10. [Verification Checklist](#verification-checklist)
11. [Common Git Commands Reference](#common-git-commands-reference)
12. [Troubleshooting](#troubleshooting)

---

## Understanding Git and GitHub

### What is Git?

**Git** is a *version control system* - software that tracks changes to your files over time. Think of it like:

- **Save points in a video game**: You can go back to any previous state
- **Track Changes in Word**: But for your entire project, not just one document
- **Time machine for code**: See what changed, when, and by whom

Git runs **locally on your computer**. You don't need internet to use Git.

### What is GitHub?

**GitHub** is a **cloud service** that hosts Git repositories online. It provides:

- **Backup**: Your code is safely stored in the cloud
- **Collaboration**: Multiple people can work on the same project
- **Social features**: Issues, pull requests, discussions
- **Security scanning**: Automated checks for vulnerabilities

**Analogy**: Git is like your local photo album. GitHub is like Google Photos - it syncs your albums to the cloud and lets you share them.

### Key Terms

| Term | Definition |
|------|------------|
| **Repository (repo)** | A project folder tracked by Git |
| **Commit** | A snapshot of your project at a point in time |
| **Branch** | A parallel version of your code |
| **Remote** | A copy of your repo on a server (like GitHub) |
| **Push** | Upload your commits to a remote |
| **Pull** | Download commits from a remote |
| **Clone** | Copy a remote repository to your computer |

---

## Tools You'll Need

### Required Tools

| Tool | Purpose | Why It's Needed |
|------|---------|-----------------|
| **git** | Version control | Core tool for tracking changes |
| **gh** (GitHub CLI) | GitHub integration | Create repos, manage settings from terminal |

### Optional Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **GitHub Desktop** | Visual Git interface | If you prefer clicking over typing commands |
| **VS Code** | Code editor with Git integration | Built-in Git panel, diff viewer |

### Why These Tools?

- **git**: The foundation. Every other tool builds on Git.
- **gh**: GitHub's official CLI. Faster than using the website for common tasks. Needed to create private repos from the command line.
- **GitHub Desktop**: Good for visualizing changes. Recommended for beginners who find the command line intimidating.

---

## Installing the Tools

### macOS

```bash
# Install Homebrew first (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Git (may already be installed via Xcode)
brew install git

# Install GitHub CLI
brew install gh

# Optional: Install GitHub Desktop
brew install --cask github
```

**Verify installation:**
```bash
git --version    # Should show: git version 2.x.x
gh --version     # Should show: gh version 2.x.x
```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Git
sudo apt install git

# Install GitHub CLI
# First, add the GitHub CLI repository
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**For other Linux distributions:**
- Fedora: `sudo dnf install git gh`
- Arch: `sudo pacman -S git github-cli`

**Verify installation:**
```bash
git --version
gh --version
```

### Windows

**Option A: Using winget (Windows 10/11)**
```powershell
# Open PowerShell as Administrator
winget install Git.Git
winget install GitHub.cli

# Optional: GitHub Desktop
winget install GitHub.GitHubDesktop
```

**Option B: Manual Download**
1. **Git**: Download from https://git-scm.com/download/windows
   - During install, keep default options
   - Select "Git from the command line and also from 3rd-party software"
2. **GitHub CLI**: Download from https://cli.github.com/
3. **GitHub Desktop** (optional): Download from https://desktop.github.com/

**Verify installation** (open new PowerShell/CMD window):
```powershell
git --version
gh --version
```

### Raspberry Pi

```bash
# Git is usually pre-installed, but update it
sudo apt update
sudo apt install git

# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

---

## Initial Git Configuration

Before using Git, you need to tell it who you are. This information appears in every commit you make.

### Set Your Identity

Run these commands (replace with your actual name and email):

```bash
# Set your name (appears in commits)
git config --global user.name "Your Name"

# Set your email (should match your GitHub account email)
git config --global user.email "your.email@example.com"
```

### Verify Your Configuration

```bash
git config --global --list
```

You should see:
```
user.name=Your Name
user.email=your.email@example.com
```

### Optional: Set Default Branch Name

Modern convention uses `main` instead of `master`:

```bash
git config --global init.defaultBranch main
```

### Optional: Set Default Editor

Git sometimes opens an editor (for commit messages, etc.):

```bash
# For VS Code
git config --global core.editor "code --wait"

# For nano (simple terminal editor)
git config --global core.editor "nano"

# For vim
git config --global core.editor "vim"
```

### Authenticate with GitHub

The GitHub CLI needs to connect to your GitHub account:

```bash
gh auth login
```

Follow the prompts:
1. Select **GitHub.com**
2. Select **HTTPS** (recommended)
3. Select **Login with a web browser**
4. Copy the one-time code shown
5. Press Enter to open your browser
6. Paste the code and authorize

**Verify authentication:**
```bash
gh auth status
```

---

## Preparing Your Project

### Step 1: Navigate to Your Project

```bash
cd /path/to/ledportal
```

### Step 2: Check Current State

Before starting, understand what files exist:

```bash
# List all files including hidden ones
ls -la        # Mac/Linux
dir /a        # Windows CMD
Get-ChildItem -Force   # Windows PowerShell
```

### Step 3: Create .gitignore

The `.gitignore` file tells Git which files to **NOT** track. This is crucial for:
- **Security**: Don't commit passwords, API keys, or secrets
- **Cleanliness**: Don't commit generated files, caches, or dependencies
- **Size**: Don't commit large binary files or virtual environments

Create `.gitignore` in your project root:

```bash
# Create the file (or edit with your preferred editor)
touch .gitignore    # Mac/Linux
type nul > .gitignore   # Windows CMD
```

**Add these contents to `.gitignore`:**

```gitignore
# ===========================================
# Python
# ===========================================

# Virtual environments (IMPORTANT - these are large!)
.venv/
venv/
env/
ENV/

# Python bytecode
__pycache__/
*.py[cod]
*$py.class
*.pyc

# Distribution / packaging
*.egg-info/
dist/
build/
eggs/
*.egg

# ===========================================
# IDE and Editor files
# ===========================================

# VS Code
.vscode/
*.code-workspace

# PyCharm / JetBrains
.idea/

# Vim
*.swp
*.swo
*~

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Windows
Thumbs.db
ehthumbs.db
Desktop.ini

# ===========================================
# Project-specific
# ===========================================

# Debug output files
last.bmp

# Snapshots (you may want to keep these - remove this line if so)
snapshot_*.bmp
snapshot_*.bin

# Local configuration overrides
config.local.yaml
*.local.py

# ===========================================
# Secrets and credentials (CRITICAL!)
# ===========================================

# Environment files with secrets
.env
.env.local
.env.*.local

# API keys or credentials
*credentials*
*secret*
*.pem
*.key

# ===========================================
# CircuitPython device files
# ===========================================

# These are on the CIRCUITPY drive, not in the repo
# But just in case someone copies them locally:
lib/
.fseventsd/
.metadata_never_index
.Trashes
```

### Step 4: Review Sensitive Files

**CRITICAL SECURITY CHECK**: Before committing, ensure you're not including:

```bash
# Search for potential secrets (Mac/Linux)
grep -r "password" --include="*.py" .
grep -r "api_key" --include="*.py" .
grep -r "secret" --include="*.py" .

# Check for credential files
find . -name "*.pem" -o -name "*.key" -o -name ".env"
```

**If you find any secrets:**
1. Move them to a `.env` file (which is gitignored)
2. Update your code to read from environment variables
3. Never commit the original file with secrets

---

## Creating the Repository

### Option A: Create Using GitHub CLI (Recommended)

This creates both the local Git repo and the private GitHub repo in one step:

```bash
# Navigate to your project directory
cd /path/to/ledportal

# Initialize Git and create private GitHub repo
gh repo create ledportal --private --source=. --push
```

**What this command does:**
- `gh repo create`: Create a new GitHub repository
- `ledportal`: Name of the repository
- `--private`: Make it private (only you can see it)
- `--source=.`: Use current directory as the source
- `--push`: Push the code immediately

**If you get an error about the directory not being a Git repo:**
```bash
# Initialize Git first
git init

# Then create the GitHub repo
gh repo create ledportal --private --source=. --remote=origin --push
```

### Option B: Create Using GitHub Website + Git Commands

1. **Go to GitHub.com** and log in
2. Click the **+** icon (top right) → **New repository**
3. Fill in:
   - Repository name: `ledportal`
   - Description: `LED Matrix Camera Feed Display System`
   - Visibility: **Private**
   - Do NOT initialize with README (we have our own)
4. Click **Create repository**
5. Follow the "push an existing repository" instructions shown:

```bash
# In your project directory
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ledportal.git
git push -u origin main
```

### Option C: Using GitHub Desktop

1. Open GitHub Desktop
2. File → Add Local Repository
3. Navigate to your ledportal folder
4. If not a Git repo, it will offer to create one - click "create a repository"
5. Fill in the name and description
6. Ensure "Keep this code private" is checked
7. Click "Create Repository"
8. Click "Publish repository" in the top bar
9. Uncheck "Keep this code private" if you want it public (leave checked for private)
10. Click "Publish Repository"

---

## Your First Commit

If you used Option A above, your first commit is already done. Otherwise:

### Stage Your Files

"Staging" means selecting which files to include in your commit:

```bash
# See what files Git sees
git status

# Stage all files (respecting .gitignore)
git add .

# Or stage specific files
git add README.md
git add sandbox/camera_feed.py
```

### Review What's Staged

```bash
# See staged files
git status

# See what changes are staged (detailed)
git diff --staged
```

### Create the Commit

```bash
git commit -m "Initial commit: LED Portal camera feed system

- Camera capture for Mac and Raspberry Pi
- Matrix Portal M4 CircuitPython receiver
- Display modes: landscape, portrait, squish, letterbox
- Snapshot feature with countdown
- High school educational version
- Professional modular version"
```

**Commit Message Best Practices:**
- First line: Short summary (50 chars or less)
- Blank line
- Body: Detailed explanation (wrap at 72 chars)
- Use present tense ("Add feature" not "Added feature")
- Explain *what* and *why*, not *how*

---

## Pushing to GitHub

If you haven't pushed yet:

```bash
# Push and set upstream (first time only)
git push -u origin main

# Future pushes just need:
git push
```

### Verify on GitHub

1. Go to https://github.com/YOUR_USERNAME/ledportal
2. You should see all your files
3. The repository should show a lock icon (🔒) indicating it's private

---

## GitHub Security Settings

Now that your code is on GitHub, configure security settings.

### Access the Security Settings

1. Go to your repository on GitHub
2. Click **Settings** (tab on the right)
3. Click **Code security and analysis** (left sidebar, under "Security")

### Enable Security Features

Check these boxes to enable:

#### ☑️ Dependency Graph
- **What it does**: Maps all your project's dependencies
- **Why enable**: Helps identify which packages you rely on
- **For this project**: Shows opencv-python, numpy, pyserial, etc.

#### ☑️ Dependabot Alerts
- **What it does**: Alerts you when dependencies have known vulnerabilities
- **Why enable**: Get notified if a package you use has a security issue
- **Action required**: You'll get emails/notifications when vulnerabilities are found

#### ☑️ Dependabot Security Updates
- **What it does**: Automatically creates pull requests to update vulnerable dependencies
- **Why enable**: Keeps your dependencies secure with minimal effort
- **Note**: Review these PRs before merging - updates can sometimes break things

#### ☑️ Secret Scanning
- **What it does**: Scans your repository for accidentally committed secrets (API keys, passwords, tokens)
- **Why enable**: Catches mistakes before they become security incidents
- **Important**: If a secret is found, it may already be compromised - rotate it immediately!

#### ☑️ Push Protection
- **What it does**: Blocks pushes that contain secrets
- **Why enable**: Prevents secrets from ever reaching GitHub
- **Note**: Can be bypassed if needed, but requires explicit acknowledgment

### Branch Protection Rules (Optional but Recommended)

Protect your main branch from accidental changes:

1. Go to **Settings** → **Branches**
2. Click **Add branch protection rule**
3. Branch name pattern: `main`
4. Consider enabling:
   - ☑️ Require a pull request before merging
   - ☑️ Require status checks to pass before merging
   - ☑️ Do not allow bypassing the above settings

**For solo projects**: You might skip this to allow direct pushes to main.
**For team projects**: Highly recommended to require pull requests.

### Review Repository Visibility

Double-check your repo is private:

1. Go to **Settings** → **General**
2. Scroll to "Danger Zone"
3. Verify it says "Change repository visibility" with "This repository is currently private"

---

## Verification Checklist

Use this checklist to ensure everything is set up correctly:

### Git Setup
- [ ] Git is installed (`git --version` works)
- [ ] GitHub CLI is installed (`gh --version` works)
- [ ] Git identity is configured (`git config --global --list` shows name/email)
- [ ] GitHub CLI is authenticated (`gh auth status` shows logged in)

### Repository Setup
- [ ] Project directory is a Git repository (`.git` folder exists)
- [ ] `.gitignore` file exists and contains appropriate entries
- [ ] No `.venv` or `__pycache__` folders are tracked
- [ ] Initial commit has been made (`git log` shows commits)
- [ ] Remote is configured (`git remote -v` shows origin URL)

### GitHub Setup
- [ ] Repository exists on GitHub
- [ ] Repository is marked as **Private** (lock icon visible)
- [ ] All files are visible on GitHub
- [ ] README.md renders correctly on GitHub

### Security Setup
- [ ] Dependency graph is enabled
- [ ] Dependabot alerts are enabled
- [ ] Dependabot security updates are enabled
- [ ] Secret scanning is enabled
- [ ] Push protection is enabled
- [ ] No secrets are in the repository (use `git log -p | grep -i password` to check)

### Verification Commands

Run these to verify your setup:

```bash
# Check Git status
git status

# Check remote configuration
git remote -v

# Check recent commits
git log --oneline -5

# Check what's being tracked
git ls-files

# Verify files that should be ignored ARE ignored
git check-ignore -v .venv/
git check-ignore -v __pycache__/
git check-ignore -v .DS_Store

# Check GitHub repo details
gh repo view
```

---

## Common Git Commands Reference

### Daily Workflow

```bash
# Check status (do this often!)
git status

# Pull latest changes (if working with others)
git pull

# Stage changes
git add filename.py       # Stage specific file
git add .                 # Stage all changes

# Commit changes
git commit -m "Description of changes"

# Push to GitHub
git push
```

### Viewing History

```bash
# View commit history
git log

# View compact history
git log --oneline

# View history with graph (useful for branches)
git log --oneline --graph --all

# View changes in a specific commit
git show abc1234
```

### Undoing Changes

```bash
# Discard changes to a file (before staging)
git checkout -- filename.py

# Unstage a file (after git add, before commit)
git reset HEAD filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes) - DANGEROUS!
git reset --hard HEAD~1
```

### Branching (for larger changes)

```bash
# Create and switch to new branch
git checkout -b feature-name

# Switch back to main
git checkout main

# Merge feature branch into main
git checkout main
git merge feature-name

# Delete branch after merging
git branch -d feature-name
```

### Working with Remotes

```bash
# View remotes
git remote -v

# Fetch changes without merging
git fetch origin

# Pull (fetch + merge)
git pull origin main

# Push a new branch
git push -u origin branch-name
```

---

## Troubleshooting

### "Permission denied (publickey)"

You need to set up SSH keys or use HTTPS:

```bash
# Switch remote to HTTPS
git remote set-url origin https://github.com/USERNAME/ledportal.git

# Re-authenticate
gh auth login
```

### "fatal: not a git repository"

You're not in a Git repository:

```bash
# Initialize Git in current directory
git init
```

### "error: failed to push some refs"

Someone else pushed changes (or you pushed from another computer):

```bash
# Pull changes first, then push
git pull --rebase
git push
```

### "Your branch is ahead of 'origin/main'"

You have local commits not yet pushed:

```bash
git push
```

### "Changes not staged for commit"

You modified files but haven't staged them:

```bash
git add .
git commit -m "Your message"
```

### Large File Errors

GitHub rejects files over 100MB:

```bash
# Check for large files
find . -size +50M -type f

# Add large files to .gitignore
echo "path/to/largefile" >> .gitignore

# If already committed, remove from history (complex!)
# Consider using Git LFS for large files
```

### Accidentally Committed Secrets

**CRITICAL**: If you committed a secret (password, API key):

1. **The secret is compromised** - assume it's been seen
2. **Rotate the secret immediately** - generate a new one
3. **Remove from history** (complex, see GitHub docs on "Removing sensitive data")
4. **Add to .gitignore** to prevent future accidents

```bash
# Quick check for common secret patterns
git log -p | grep -E "(password|secret|api_key|token)" -i
```

---

## Next Steps

After completing this setup:

1. **Make changes** to your code
2. **Commit regularly** (small, logical commits are better)
3. **Push daily** (or more often) to keep GitHub backup current
4. **Review Dependabot alerts** when you receive them
5. **Learn branching** for larger features

### Recommended Learning Resources

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Skills](https://skills.github.com/) - Interactive tutorials
- [Oh Shit, Git!?!](https://ohshitgit.com/) - Fixing common mistakes
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit message standards

---

*This guide was created for the LED Portal project. Last updated: 2024*
