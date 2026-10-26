---
description: Route swift-library website changes to their catalog, presentation and pipeline owners and keep sources, outputs and caches apart.
---
# Website Agent Guide

Read `README.md` for the site's purpose, build, preview, and validation commands.

## Ownership and routing

- `projects.json` owns catalog structure. GitHub metadata owns repository
  descriptions, versions, releases, and public membership.
- `templates/` and `assets/` own website presentation. The organization
  `DESIGN.md` owns shared visual decisions and the icon source.
- `scripts/` owns the pipeline and checks; `Tests/` owns their regression tests.
- Package APIs and DocC source belong to their package repositories. Build-time
  presentation transforms must preserve those sources and their manifests.

## Working rules

- Keep source, output, and cache roles distinct. Reuse producer-owned ignored
  output directories; never copy a full checkout or its Git directory into
  generated output or caches. Build package documentation in its repository,
  a Git worktree, or an archive of the selected revision.
- Preserve license and ownership records. Keep paths, tokens, local context,
  and execution state out of published content.
