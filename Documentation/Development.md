# Site development

`projects.json` owns catalog membership, ordering, logo locations, installation
kinds, and documentation selection. The organization’s `profile/catalog.json`
owns the promise, secondary line, description, reviewed groups and navigation.
The builder and checks require a matching organization login and exact group
order. All public non-fork repositories except `.github` have project cards.
The catalog's labeled Documentation, Contributing, Security and Support links
appear in the footer alongside the site's license, contributors and versioning
links. `github-workflows` and the website link to their READMEs and use the
existing `git` installation kind to offer a clone command.
The umbrella icon heads the catalog; the
organization avatar remains the favicon. Build-time GitHub metadata supplies
public repository membership, descriptions, tags, releases, and contributor names.
The site publishes DocC for released packages and links other projects to
their READMEs.

## Build and check

Use Python 3.12 or later, Git, Xcode with Swift and DocC, and GitHub authentication through
`GH_TOKEN`, `GITHUB_TOKEN`, or the GitHub CLI. The Pages workflow owns the CI
runner and Xcode selection.

```sh
scripts/build-site --jobs 2
scripts/check-site --local
scripts/check-site
python3 -m unittest discover -s Tests -v
scripts/check-workflows
```

`_site/` contains generated pages. `.site-cache/` contains documentation build
inputs and outputs. Both are ignored. `scripts/check-site` validates generated
links, public catalog membership and ordering, GitHub descriptions and licenses,
and the contributing and attribution pages. It needs current GitHub access.
Use `--local` before the site's first publication to check generated structure,
configured catalog entries and the source license without GitHub queries. The
full check remains required after bootstrap and for deployment; it verifies
live repository membership, descriptions,
licensing and profile ordering.

Documentation comes from the latest tagged source for packages with a
published release, including prereleases. The builder discovers public library
products from each tagged manifest and merges multi-module documentation.
Source archives are downloaded at the tag's full commit SHA and removed after
conversion. No repository checkout is copied into the build cache.

A DocC catalog entry may select `traits` from its tagged package, including
`default` when it needs the default APIs. The compiler emits public symbol graphs
during that selected build. Omitted traits keep the package defaults. Symbol
graphs include extensions to external types so those APIs remain linkable in DocC.
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
`DESIGN.md`, `--profile-file` with its `profile/catalog.json`, and
`--identity-root` with the parent of the package checkouts. `scripts/check-site`
accepts the same `--profile-file` for a local presentation preview.
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
  distributed with its [SIL Open Font License](../assets/fonts/OFL.txt).
- The organization artwork is derived from the organization design source;
  its source and attribution belong to the
  [brand assets](https://github.com/swift-library/.github/tree/master/Brand/Avatar).
- `scripts/` owns build, metadata, and validation behavior. `Tests/` owns
  pipeline regression coverage.

## Deployment

`.github/workflows/pages.yml` validates pull requests and builds on pushes to
`master` or manual dispatch. `refresh.yml` dispatches validation weekly so the
catalog and tagged documentation stay current. Pull-request title and body
edits run only `source-policy.yml`, preserving the separate required
`policy / policy` check. The required `result` job aggregates workflow-schema
validation and the complete site build and live checks.

`publish.yml` reads the archive from a successful default-branch Pages run,
excluding pull requests and foreign source repositories. The validated source
must still match the publication workflow's default-branch commit. It queues
deployments without cancelling running or pending publications. The build job
reads source and metadata; publication holds Pages and OIDC permissions.
Configure GitHub Pages to deploy through Actions.
