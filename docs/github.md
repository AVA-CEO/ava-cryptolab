# Connect AVA CryptoLab to GitHub

Git is a local history of the project. GitHub is a remote place to store that history. Creating commits does not publish them; pushing sends them to GitHub.

Author identity is configured **only for this repository** with the owner-confirmed name and email. Review it with:

```powershell
git config --local user.name
git config --local user.email
git log --oneline
git status
```

## Create and connect

1. Sign in to GitHub.
2. Click **New repository** and name it `ava-cryptolab`.
3. Choose **Private** while preparing the portfolio. Do not initialize a README, licence or `.gitignore`; those already exist locally, with licensing still pending approval.
4. Create the repository. Copy its HTTPS URL.
5. In the project root in VS Code’s terminal, run:

```powershell
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/ava-cryptolab.git
git remote -v
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username; an email address is not a username. This command connects the address but **does not upload any code**. If `origin` already exists, inspect it before deciding whether to use `git remote set-url origin ...`.

When you decide to upload the code, the command is:

```powershell
git push -u origin main
```

No push, repository creation or public publication has been performed by the agent. The agent must obtain explicit authorization before doing those actions. You can run the push command yourself when ready. GitHub may prompt you to sign in using its credential manager; do not paste access tokens into source files or chat.

Ignored data includes `.env` files, local SQLite databases, environments, build output, uploads, logs, CSV trade exports and designated private/credential folders. `.env.example` is intentionally tracked and contains no secrets. Check `git status` before every commit; ignore rules cannot identify every possible private filename automatically.
