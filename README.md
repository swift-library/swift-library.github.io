<div align="center">

<p align="center">
  <a href="https://github.com/swift-library/swift-library.github.io"><img src="https://raw.githubusercontent.com/swift-library/.github/master/Documentation/Assets/Logo.svg" width="160" alt="swift-library.github.io logo"></a>
</p>

<h1 align="center">swift-library.github.io</h1>

<p align="center">
  Find Swift packages, copy install commands, and read their API documentation.
</p>

<p align="center">
  <a href="https://github.com/swift-library/swift-library.github.io/actions/workflows/pages.yml"><img src="https://github.com/swift-library/swift-library.github.io/actions/workflows/pages.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="LICENSE.txt"><img src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat" alt="License: Apache-2.0 WITH Swift-exception"></a>
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#quick-look">Quick look</a> ·
  <a href="#install">Install</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#requirements">Requirements</a> ·
  <a href="#documentation">Documentation</a> ·
  <a href="#contributing">Contributing</a> ·
  <a href="#license">License</a>
</p>

</div>

## Overview

Read API docs for an installable release, with each package’s own landing-page identity intact. Repository descriptions and release links stay aligned with GitHub; the [site guide](Documentation/Development.md) covers catalog coverage, builds, preview, and deployment.

## Quick look

Build and serve a local catalog:

```sh
scripts/build-site --jobs 2
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

## Install

Clone this repository to build or edit the site:

```sh
git clone https://github.com/swift-library/swift-library.github.io.git
cd swift-library.github.io
```

Visitors can browse the [published catalog](https://swift-library.github.io/) directly.

## Usage

Edit catalog structure in `projects.json` and presentation in `templates/` and `assets/`. Run `scripts/build-site`, then `scripts/check-site`; the [development guide](Documentation/Development.md) explains metadata inputs, DocC selection, caches, and preview checks.

## Requirements

- Python 3.12 or later and Git
- macOS with Xcode, Swift, and DocC for package documentation builds
- GitHub access through the existing GitHub CLI login or a workflow token

The Pages workflow declares the tested runner and Xcode selection.

## Documentation

- [Site development](Documentation/Development.md): building, previewing, catalog configuration, and deployment
- [Organization standards](https://github.com/swift-library/.github)

## Contributing

See the [contributing page](templates/contributing.html) and [organization contribution guide](https://github.com/swift-library/.github/blob/master/CONTRIBUTING.md). Run the checks in the [site development guide](Documentation/Development.md) before submitting changes.

## License

The site uses [Apache-2.0 WITH Swift-exception](LICENSE.txt). The font retains its [SIL Open Font License](assets/fonts/OFL.txt). See [NOTICE](NOTICE) for ownership.
