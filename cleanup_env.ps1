# --- CONFIG ---
$RepoUrl = "https://github.com/drcartlidge/job_hunter.git"  # <-- change if needed
$Branch = "main"  # update if your repo uses 'master'

# --- 1. Backup the repo ---
Write-Host "Cloning backup..."
git clone --mirror $RepoUrl repo-backup

# --- 2. Clone fresh working copy ---
Write-Host "Cloning working copy..."
git clone $RepoUrl repo-clean
Set-Location repo-clean

# --- 3. Ensure git-filter-repo is installed ---
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found, installing via pip..."
    pip install git-filter-repo
}

# --- 4. Scrub .env from history ---
Write-Host "Removing .env from history..."
git filter-repo --invert-paths --path .env

# --- 5. Add .env to .gitignore ---
Write-Host "Updating .gitignore..."
".env" | Out-File -FilePath ".gitignore" -Encoding UTF8 -Append
git add .gitignore
git commit -m "Ignore .env file"

# --- 6. Push cleaned history back ---
Write-Host "Force pushing cleaned repo to origin..."
git push origin --force --all
git push origin --force --tags

Write-Host "✅ Cleanup complete. Now rotate your API keys and passwords immediately."
