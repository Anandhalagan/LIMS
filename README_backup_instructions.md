Project backup to GitHub

This repository snapshot is prepared as a backup of the LIMS project.

What I added for the backup process:

- `.gitignore` — excludes virtual environments, build artifacts, report PDFs, database files, and the encryption key. This prevents sensitive or bulky files from being committed.

How to push this backup to GitHub (manual steps):

1) Create a new repository on GitHub (via website) named `LIMS-backup` (or your preferred name).
2) Add the remote and push from this local repo (replace <YOUR_REMOTE_URL> with the HTTPS or SSH URL):

   # If you haven't initialized the repo yet (the script below may have already run this)
   git init
   git add .
   git commit -m "Initial backup commit"

   # Add remote and push
   git remote add origin <YOUR_REMOTE_URL>
   git branch -M main
   git push -u origin main

Alternative: use GitHub CLI (if installed and authenticated):

   gh repo create my-username/LIMS-backup --public --source=. --remote=origin --push

Security notes:
- The `.gitignore` excludes `encryption_key.key` and `lab.db` backups; ensure you DO NOT commit any encryption keys or production databases.
- If you want to include specific data files, review them and remove sensitive items from `.gitignore` intentionally.

If you'd like, I can:
- Add the remote and push for you (you must provide the remote URL or authenticate with `gh` on this machine).
- Create a GitHub repo using `gh` if you authorize (it requires your GitHub authentication).

Next steps I can take now:
- Initialize the repo locally and create an initial commit (I'll do this now unless you say otherwise).
- Add remote and push if you provide the remote URL or allow me to use `gh`.
