# Website Agent Guide

Read `README.md` for the site's purpose, build, preview, and validation commands.

## Ownership and routing

- `projects.json` owns catalog structure. GitHub metadata owns repository
  descriptions, versions, releases, and public membership.
- `templates/` and `assets/` own website presentation. The organization
  `DESIGN.md` owns shared visual decisions and the icon source.
- `Scripts/` owns the pipeline and checks; `Tests/` owns their regression tests.
- Package APIs and DocC source belong to their package repositories. Build-time
  presentation transforms must preserve those sources and their manifests.

## Working rules

- Keep source, output, and cache roles distinct. Reuse producer-owned ignored
  output directories; never copy a full checkout or its Git directory into
  generated output or caches. Build package documentation in its repository,
  a Git worktree, or an archive of the selected revision.
- Preserve license and ownership records. Keep paths, tokens, local context,
  and execution state out of published content.
- Before handoff, ensure current artifacts describe accepted behavior without
  requiring readers to know the editing conversation.

## Code Review Rules

### Source of truth

- Flag catalog copy or version values duplicated from GitHub metadata because
  they drift when projects release. Safe path: derive those values at build time.

### Claims and documentation

- Flag capability, platform, or release claims unsupported by package sources
  and verification. Safe path: use the owning package's verified facts and
  link to its documentation.
- Flag documentation transforms that change package behavior or erase existing
  identity metadata. Safe path: preserve package-owned content and apply only
  the declared presentation defaults.

### Interaction and accessibility

- Flag navigation, content, or installation instructions that become inaccessible
  without JavaScript, keyboard input, or in a supported appearance. Safe path:
  preserve semantic HTML, visible focus, sufficient contrast, and a readable
  installation command alongside clipboard enhancement.

### Validation

- Flag behavior changes without regression coverage for the changed pipeline
  contract. Safe path: add a focused test in `Tests/` and run the declared checks.
