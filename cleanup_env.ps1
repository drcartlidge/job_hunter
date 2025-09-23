# --- CONFIG ---
$RepoUrl = "https://github.com/drcartlidge/job_hunter.git"  # <-- change if needed
$Branch = "main"  # update if your repo uses 'master'

# --- 1. Backup the repo ---
Write-Host "Cloning backup..."
git clone --mirror $RepoUrl job_hunter-backup-env-example

# --- 2. Clone fresh working copy ---
Write-Host "Cloning working copy..."
git clone $RepoUrl job_hunter-clean-env-example
Set-Location job_hunter-clean-env-example

# --- 3. Ensure git-filter-repo is installed ---
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found, installing via pip..."
    pip install git-filter-repo
}

# --- 4. Scrub .env.example from history ---
Write-Host "Removing .env.example from history..."
git filter-repo --invert-paths --path .env.example

# --- 5. Update .gitignore to ignore .env.example if needed ---
Write-Host "Ensuring .env.example is ignored..."
".env.example" | Out-File -FilePath ".gitignore" -Encoding UTF8 -Append
git add .gitignore
git commit -m "Ignore .env.example"

# --- 6. Push cleaned history back ---
Write-Host "Force pushing cleaned repo to origin..."
git push origin --force --all
git push origin --force --tags

Write-Host "✅ Cleanup complete. .env.example removed from history."
