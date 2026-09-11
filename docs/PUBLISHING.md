# Publish the interactive guide on GitHub

GitHub stores the public source. **GitHub Pages hosts the interactive website**, so readers need only a browser and the published link. Opening the repository itself displays source files; Pages provides the running guide.

The package includes `.github/workflows/pages.yml`. On a push to `main`, this workflow checks the reviewed manifest, builds a static public website and publishes it with GitHub Pages. No home server, inbound router rule, VPN, Python installation or login is needed for readers of the public website. GitHub Pages is available for public repositories on GitHub Free. [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## First publication using the GitHub website

1. Extract the **updated public release ZIP** into a new folder. Work only with the extracted contents, never with a parent workspace containing photographs or private configuration.
2. On GitHub, create a new **public** repository, for example `isolated-lab-guide`. Start empty: do not add GitHub's generated README, license or gitignore. The reviewed package already includes its README and gitignore; unrelated added files make the manifest check fail.
3. Upload the **contents** of the extracted folder to the repository root, not the ZIP and not a containing `share/` folder. Use the empty repository's upload link, or **Add file → Upload files**. Complete the hidden-file procedure below for `.gitignore` and `.github/workflows/pages.yml`; showing hidden files in a file manager does not guarantee that browser drag-and-drop accepts them. The root must contain `README.md`, `PUBLIC_MANIFEST.json`, `app/`, `tools/` and the hidden files. Commit to `main`. [GitHub file upload instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
4. Open repository **Settings → Pages**. Under **Build and deployment**, set **Source → GitHub Actions**. This selects the included workflow; do not choose a Jekyll template or a branch-based source. [GitHub publishing-source settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
5. Open **Actions → Publish interactive guide → Run workflow**, select `main`, and run it. The first automatic run may have failed because Pages was not enabled yet; the new run handles that.
6. Wait for both `build` and `deploy` to finish successfully. The deployment and **Settings → Pages** show the actual website URL. A normal project URL has the form `https://ACCOUNT.github.io/isolated-lab-guide/`.
7. Open that URL in a private/incognito window. Check a scenario, another site, a reference chapter and **Print / PDF**. Put the URL in the repository's **About → Website** field and share it with readers.

The repository and Pages URL identify the publishing GitHub account. Removing home-network details does not make the account anonymous. The guide has no telemetry or data-upload endpoint; GitHub receives ordinary hosting requests. Sensitive inventory and runtime secrets belong in the local edition.

## Hidden files in a browser upload

Hidden entries can be omitted by the file picker or rejected during browser upload. If `.gitignore` or the `.github` directory did not arrive, create their files with GitHub's editor using the **exact released content**:

1. Open the extracted `.gitignore` in a plain-text editor. On Linux, **Ctrl+H** reveals hidden items in the file manager. Copy the complete file.
2. At the repository root, choose **Add file → Create new file**. Enter `.gitignore` as the filename, paste the original content without Markdown fences or edits, and commit it to `main`.
3. Open the extracted `.github/workflows/pages.yml` locally and copy its complete content. Create another new file named `.github/workflows/pages.yml` at the repository root. The `/` characters create the folders. Preserve indentation, line endings and the final newline; commit the original workflow to `main`.
4. Verify both paths in the repository's file tree before running Pages. If either already exists, compare its content with the release rather than creating a renamed duplicate. A manifest mismatch is corrected by restoring the exact original or by using the Git upload method below.

GitHub documents creating nested files through the filename field in its [new-file instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/creating-new-files). Browser upload is limited to 100 files per operation, so larger releases need batches or the Git workflow. Git preserves hidden paths during normal staging; the file-manager visibility setting is irrelevant to `git add .`. [GitHub upload limits and Git alternative](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)

## What readers do

For the interactive guide, open the Pages link. Nothing is installed and no terminal is required. Scenario switches, address planning, figure downloads and browser PDF printing run in the browser.

For device code, use the repository's **Code → Download ZIP** or clone it, then follow the relevant firmware/network/game chapter. Publishing the guide does not run the hardware programs or connect a real lab.

For an offline local copy, extract the source ZIP, open a terminal in that extracted folder and run:

```sh
python3 tools/serve.py
```

Open `http://127.0.0.1:8765`. The local server and Python are needed only for this offline option.

## Git / command-line alternative

Git and GitHub CLI must already be installed. Authenticate with the official browser login flow rather than putting a token in a command:

```sh
gh auth login --web --git-protocol https
gh auth setup-git
```

From the **new extracted public folder**, verify the package and initialise a repository. Git needs a commit name and email; configure the GitHub-provided noreply address from account email settings if the personal email should not appear in commits.

```sh
python3 tools/release.py check
git init -b main
git add .
git commit -m "Publish isolated lab guide"
gh repo create isolated-lab-guide --public --source=. --remote=origin --push
```

The last command creates the public repository and uploads the files; execute it only when the public contents are ready. Continue with Settings → Pages → GitHub Actions and run the workflow as above. [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create), [GitHub CLI login](https://cli.github.com/manual/gh_auth_login)

## Updating the guide

Review all public edits locally, then update the manifest before committing:

```sh
python3 tools/release.py manifest --reviewed-public-content
python3 tools/release.py check
```

Commit the changed public source and manifest together. A push to `main` triggers a new deployment. Do not let the workflow regenerate the manifest automatically: it verifies the review boundary.

The manifest checks the site build, not what GitHub already stores. Never commit private information just because deployment would refuse it; a public commit already publishes that information.

If editing only through the GitHub website, download the updated repository, review it locally, regenerate the manifest there, and upload that manifest with the reviewed changes. Failed checks should be corrected rather than removed.

## Troubleshooting

| Symptom | Check |
|---|---|
| No workflow appears | Include the hidden `.github/workflows/pages.yml` and commit it to the default branch |
| Hidden file/folder is rejected or missing | Use Add file → Create new file with exact original contents, or use the Git workflow |
| Workflow never starts on a push | The supplied trigger is `main`; use that branch or review/update the workflow |
| Build says `tools/build_pages.py` is missing | Public contents must be at repository root, not nested under `share/` |
| Manifest mismatch | Missing hidden gitignore, changed line endings, edited files or extra generated files; review the difference and regenerate locally |
| Deployment fails before Pages exists | Select Settings → Pages → GitHub Actions, then run the workflow again |
| Organisation blocks an action | Organisation settings must allow the official GitHub Pages actions used by this workflow |
| Website returns 404 | Wait for the successful deployment; use the exact URL shown in Pages settings |
| Old content appears | Check the latest workflow run and reload the page |
| Local inventory is absent online | Expected: the static site has no private API or inventory files |

## Verify a static build locally

The website builder creates a new directory outside the public source tree:

```sh
python3 tools/build_pages.py --output /tmp/lab-pages-preview
python3 -m http.server 8766 --bind 127.0.0.1 --directory /tmp/lab-pages-preview
```

Open `http://127.0.0.1:8766`. This generic preview server serves only the generated public artifact. Never point it at a workspace containing private files. Stop with Ctrl+C.

Research checked 2026-09-11. The workflow files are prepared locally; no repository creation or deployment happens until the publishing steps are performed.
