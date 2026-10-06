# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
"""Prepare archive sources and apply missing DocC presentation defaults."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.request import Request, urlopen

from site_support import SiteError

PIPELINE_SOURCE = Path(__file__).read_text()


def design_colors(design):
    blocks = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", design, re.S)]
    families = [block["icons"] for block in blocks if "icons" in block]
    if len(families) != 1:
        raise SiteError("DESIGN must contain one icon family")
    ranges = [(int(start), int(end), color) for start, end, color in re.findall(
        r"^\| (\d+) to (\d+) \| `([a-z]+)` \|$", design, re.M)]
    if not ranges:
        raise SiteError("DESIGN has no DocC hue-to-color mapping")
    result = {}
    for name, icon in families[0].items():
        hue = icon["hue"] % 360
        matches = [color for start, end, color in ranges
                   if (start <= hue < end if start < end else hue >= start or hue < end)]
        if len(matches) != 1:
            raise SiteError(f"DESIGN hue for {name} must map to exactly one DocC color")
        result[name] = matches[0]
    return result


@contextmanager
def archive_source(organization, repository, revision, cache):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SiteError("Documentation source requires a full commit SHA")
    if not hasattr(tarfile, "data_filter"):
        raise SiteError("Source archive extraction requires Python 3.12 or later")
    work = cache / "source-archives" / repository
    source = work / "source"
    archive = work / "source.tar.gz"
    work.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.rmtree(source)
    source.mkdir()
    try:
        # Public archives use a credential-free download from GitHub's archive host.
        request = Request(f"https://codeload.github.com/{organization}/{repository}/tar.gz/{revision}",
                          headers={"User-Agent": "swift-library-site"})
        with urlopen(request, timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with tarfile.open(archive) as bundle:
            bundle.extractall(source, filter="data")
        roots = list(source.iterdir())
        if len(roots) != 1 or not roots[0].is_dir() or roots[0].is_symlink():
            raise SiteError("Source archive must have one repository root")
        if any(path.name == ".git" for path in roots[0].rglob("*")):
            raise SiteError("Source archive contains Git metadata")
        yield roots[0]
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(source, ignore_errors=True)


def visible_markdown(text):
    """Mask code fences and comments without changing source offsets."""
    lines = text.splitlines(keepends=True)
    result = []
    fence = None
    for line in lines:
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            result.append("".join("\n" if char == "\n" else " " for char in line))
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not line[marker.end():].strip():
                fence = None
        elif marker:
            fence = marker[1]
            result.append("".join("\n" if char == "\n" else " " for char in line))
        else:
            result.append(line)
    return re.sub(r"<!--.*?-->", lambda match: "".join("\n" if char == "\n" else " " for char in match[0]),
                  "".join(result), flags=re.S)


def landing_page(catalog, module):
    pattern = re.compile(r"^#\s+``" + re.escape(module) + r"``\s*$", re.M)
    candidates = [path for path in catalog.glob("*.md") if pattern.search(visible_markdown(path.read_text()))]
    if len(candidates) > 1:
        raise SiteError(f"Multiple DocC landings for {module}")
    if candidates:
        return candidates[0]
    landing = catalog / (module + ".md")
    if landing.exists():
        raise SiteError(f"Cannot replace a non-module article at {landing.name}")
    landing.write_text(f"# ``{module}``\n")
    return landing


def add_identity(catalog, module, color, icon):
    """Add missing metadata while retaining the tagged landing's own directives."""
    catalog.mkdir(parents=True, exist_ok=True)
    landing = landing_page(catalog, module)
    text = landing.read_text()
    # Fenced examples do not declare the landing's metadata.
    visible = visible_markdown(text)
    additions = []
    if not re.search(r"@PageImage\s*\([^)]*\bpurpose\s*:\s*icon\b", visible):
        name = module.lower() + "-site-icon.png"
        resources = catalog / "Resources"
        resources.mkdir(exist_ok=True)
        destination = resources / name
        if destination.exists() and destination.read_bytes() != icon:
            raise SiteError(f"DocC resource name collision: {name}")
        destination.write_bytes(icon)
        additions.append(f'  @PageImage(purpose: icon, source: "{name}", alt: "{module} icon")')
    if not re.search(r"@PageColor\s*\(", visible):
        additions.append(f"  @PageColor({color})")
    if additions:
        metadata = re.search(r"@Metadata\s*\{", visible)
        if metadata:
            offset = metadata.end()
            text = text[:offset] + "\n" + "\n".join(additions) + text[offset:]
        else:
            heading = re.search(r"^#\s+``" + re.escape(module) + r"``[^\n]*", text, re.M)
            offset = heading.end()
            text = text[:offset] + "\n\n@Metadata {\n" + "\n".join(additions) + "\n}" + text[offset:]
        landing.write_text(text)
    return landing


def merged_identity(archive, repository, color, icon):
    path = archive / "data/documentation.json"
    document = json.loads(path.read_text())
    metadata = document.setdefault("metadata", {})
    metadata.setdefault("color", {"standardColorIdentifier": color})
    if not any(image.get("type") == "icon" for image in metadata.get("images", [])):
        identifier = repository + "-site-icon.png"
        target = archive / "images" / "site" / identifier
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(icon)
        metadata.setdefault("images", []).append({"type": "icon", "identifier": identifier})
        document.setdefault("references", {})[identifier] = {
            "type": "image", "identifier": identifier, "alt": repository + " icon",
            "variants": [{"traits": ["1x", "light"], "url": "/images/site/" + identifier}]}
    path.write_text(json.dumps(document, ensure_ascii=False) + "\n")


def identity_records(archive, modules, merged, repository=None):
    landings = ["data/documentation/" + module.lower() + ".json" for module in modules]
    if merged:
        landings.append("data/documentation.json")
    records = []
    for landing in landings:
        document = json.loads((archive / landing).read_text())
        color = document.get("metadata", {}).get("color", {}).get("standardColorIdentifier")
        icons = [entry for entry in document.get("metadata", {}).get("images", []) if entry.get("type") == "icon"]
        if not color or not icons:
            raise SiteError(f"DocC landing has no icon/color identity: {landing}")
        assets = []
        for icon in icons:
            reference = document["references"][icon["identifier"]]
            for variant in reference["variants"]:
                relative = variant["url"].lstrip("/")
                if repository and relative.startswith(repository + "/"):
                    relative = relative[len(repository) + 1:]
                target = (archive / relative).resolve()
                if not target.is_relative_to(archive.resolve()) or not target.is_file():
                    raise SiteError(f"Invalid DocC icon asset: {relative}")
                assets.append({"url": variant["url"], "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        if not assets:
            raise SiteError(f"DocC landing has no icon variants: {landing}")
        records.append({"landing": landing, "color": color, "icons": assets})
    return records
