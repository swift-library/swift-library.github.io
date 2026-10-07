# swift-library website

The project catalog and documentation site for [swift-library](https://github.com/swift-library).

`projects.json` owns catalog groups, ordering, logo locations, installation
kinds, and documentation selection. Build-time GitHub metadata supplies public
repository membership, descriptions, tags, releases, and contributor names.
The site publishes DocC for released packages and links other projects to
their READMEs.

## Build and check

Use Python 3.12 or later, Git, Xcode with Swift and DocC, and GitHub authentication through
`GH_TOKEN`, `GITHUB_TOKEN`, or the GitHub CLI. The Pages workflow owns the CI
runner and Xcode selection.

```sh
Scripts/build-site --jobs 2
Scripts/check-site --local
Scripts/check-site
python3 -m unittest discover -s Tests -v
actionlint .github/workflows/pages.yml
```

`_site/` contains generated pages. `.site-cache/` contains documentation build
inputs and outputs. Both are ignored. `Scripts/check-site` validates generated
links, public catalog membership and ordering, GitHub descriptions and licenses,
and the contributing and attribution pages. It needs current GitHub access.
Use `--local` before the site's first publication to check generated structure,
configured catalog entries and the source license without GitHub queries. The
full check remains required after bootstrap and for deployment; it verifies
live repository membership, descriptions, licensing and profile ordering.

Documentation comes from the latest tagged source for packages with a
published release, including prereleases. The builder discovers public library
products from each tagged manifest and merges multi-module documentation.
Source archives are downloaded at the tag's full commit SHA and removed after
conversion. No repository checkout is copied into the build cache.

A DocC catalog entry may select `traits` from its tagged package, including
`default` when it needs the default APIs. Both compilation and symbol extraction
use that selection. Omitted traits keep the package defaults. Symbol extraction
includes extensions to external types so those APIs remain linkable in DocC.
Generated breadcrumbs omit external-type containers for which DocC emits no
page, while keeping the package's actual extension members. The link checker
distinguishes tutorial chapter labels from navigable tutorial pages; explicit
content links still require a real destination.

For landings without their own identity, the builder adds the repository's
current `Logo.png` and derives the named DocC color from the organization's
`DESIGN.md`. Existing package directives remain authoritative. A synthesized
multi-module landing receives the same defaults. Cache keys include the source
revision, toolchain, documentation selection, identity, and conversion code;
checks verify every landing's metadata and icon bytes against the build receipt.

To preview unmerged organization artwork, pass `--design-file` with its local
`DESIGN.md` and `--identity-root` with the parent of the package checkouts.
Deployment uses the public default-branch sources and does not set those options.

## Preview

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

Open `http://127.0.0.1:8765/`. Check the homepage, contributing page, and 404 page
at desktop and mobile widths in light and dark system appearances. Verify
keyboard focus and the installation copy buttons. The catalog remains usable
when JavaScript or clipboard access is unavailable.

## Edit

- `templates/` owns semantic page markup and copy. Templates use Python
  `string.Template`; preserve the existing variables.
- `assets/site.css` owns layout and appearance. It follows the organization
  [DESIGN.md](https://github.com/swift-library/.github/blob/master/DESIGN.md).
- `assets/copy.js` copies installation commands. The system color preference
  controls appearance through CSS.
- `assets/fonts/InterVariable.woff2` is the unmodified Inter 4.1 variable font,
  distributed with its [SIL Open Font License](assets/fonts/OFL.txt).
- The organization artwork is derived from the organization design source;
  its source and attribution belong to the
  [brand assets](https://github.com/swift-library/.github/tree/master/Brand/Avatar).
- `Scripts/` owns build, metadata, and validation behavior. `Tests/` owns
  pipeline regression coverage.

## Deployment

`.github/workflows/pages.yml` validates pull requests and builds on pushes to
`master`, weekly, or manual dispatch. Only a successful default-branch build can
deploy. The `result` job aggregates policy and build validation. The build job reads source and metadata; the deployment job holds
Pages and OIDC permissions. Configure GitHub Pages to deploy through Actions.

## Contributing and license

See the [contributing page](templates/contributing.html) and the organization's
[contribution guide](https://github.com/swift-library/.github/blob/master/CONTRIBUTING.md).
The site uses [Apache-2.0 WITH Swift-exception](LICENSE.txt). The font retains its
separate license. Public contributor names are generated with
`Scripts/generate-contributors`.
