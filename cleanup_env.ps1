# --- CONFIG ---
$RepoUrl = "https://github.com/drcartlidge/job_hunter.git"  # <-- change if needed
$Branch = "main"  # update if your repo uses 'master'

# --- 1. Backup the repo ---
Write-Host "Cloning backup..."
git clone --mirror $RepoUrl job_hunter-backup

# --- 2. Clone fresh working copy ---
Write-Host "Cloning working copy..."
git clone $RepoUrl job_hunter-clean
Set-Location job_hunter-clean

# --- 3. Ensure git-filter-repo is installed ---
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found, installing via pip..."
    pip install git-filter-repo
}

# --- 4. Scrub sensitive files from history ---
Write-Host "Removing .env and .zip files from history..."
git filter-repo --invert-paths --path .env --path-glob '*.zip'

# --- 5. Update .gitignore ---
Write-Host "Updating .gitignore..."
@"
.env
*.zip
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
git add .gitignore
git commit -m "Ignore .env and zip files"

# --- 6. Push cleaned history back ---
Write-Host "Force pushing cleaned repo to origin..."
git push origin --force --all
git push origin --force --tags

Write-Host "✅ Cleanup complete. .env and .zip files removed from history. Now rotate any exposed keys!"
