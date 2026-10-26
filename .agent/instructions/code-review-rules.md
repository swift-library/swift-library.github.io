---
description: Flag website changes that duplicate GitHub metadata, overstate package facts, alter package documentation, or regress accessibility.
---
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
