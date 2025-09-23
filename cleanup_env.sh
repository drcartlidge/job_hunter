#!/bin/bash
set -e

# --- CONFIG ---
REPO_URL="https://github.com/drcartlidge/job_hunter.git"   # <-- change this
BRANCH="main"                                     # <-- change if using another default branch

# --- 1. Backup the repo ---
echo "Cloning backup..."
git clone --mirror "$REPO_URL" repo-backup

# --- 2. Clone fresh working copy ---
echo "Cloning working copy..."
git clone "$REPO_URL" repo-clean
cd repo-clean

# --- 3. Install git-filter-repo if missing ---
if ! command -v git-filter-repo &> /dev/null; then
  echo "git-filter-repo not found, installing with pip..."
  pip install git-filter-repo
fi

# --- 4. Scrub .env from history ---
echo "Removing .env from history..."
git filter-repo --invert-paths --path .env

# --- 5. Add .env to .gitignore ---
echo "Updating .gitignore..."
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Ignore .env file"

# --- 6. Push cleaned history back ---
echo "Force pushing cleaned repo to origin..."
git push origin --force --all
git push origin --force --tags

echo "✅ Cleanup complete. Now rotate your API keys and passwords immediately."
