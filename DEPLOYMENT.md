# GitHub deployment notes

This repository layout is prepared for `Phaviwylera/scalarspace`.

1. Copy these files and folders to the repository root (do not nest the project folder).
2. Commit and push to the existing default branch (`main` or `master`).
3. In GitHub, open **Settings → Pages** and choose **GitHub Actions** as the build/deployment source if that is not already selected.
4. Open **Actions → Deploy Scalar Lab to GitHub Pages** and confirm the workflow completes successfully.
5. The expected project site URL is `https://phaviwylera.github.io/scalarspace/`.

The workflow publishes only the repository root as a static site. The Python CLI and local server remain source files for local use; GitHub Pages does not run Python server processes.

No repository contents have been pushed by preparing this package. Review and merge the files into the target repository before treating the site as live.
