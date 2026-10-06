#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
"""Resolve links in HTML, CSS, and DocC render data against a static site."""

from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urlsplit


class HTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.anchors = set()
        self.repositories = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        for key in ("href", "src", "poster"):
            if attributes.get(key):
                self.links.append(attributes[key])
        if attributes.get("srcset") and not attributes["srcset"].startswith("data:"):
            self.links.extend(item.strip().split()[0] for item in attributes["srcset"].split(","))
        if attributes.get("id"):
            self.anchors.add(attributes["id"])
        if tag == "a" and attributes.get("name"):
            self.anchors.add(attributes["name"])
        if tag == "article" and attributes.get("data-repository"):
            self.repositories.append(attributes["data-repository"])


def json_anchors(value):
    result = set()
    if isinstance(value, dict):
        if isinstance(value.get("anchor"), str):
            result.add(value["anchor"])
        for child in value.values():
            result.update(json_anchors(child))
    elif isinstance(value, list):
        for child in value:
            result.update(json_anchors(child))
    return result


class Links:
    def __init__(self, root, site_url):
        self.root = root.resolve()
        self.host = urlsplit(site_url).netloc
        self.documents = {}
        self.errors = []
        self.count = 0

    def html(self, path):
        if path not in self.documents:
            document = HTML()
            document.feed(path.read_text())
            self.documents[path] = document
        return self.documents[path]

    def resolve(self, url, source, scope=None):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme not in {"", "http", "https"} or parsed.netloc != self.host:
                return None
        path = unquote(parsed.path)
        namespaces = ("/documentation", "/tutorials", "/images", "/videos", "/downloads")
        if scope and any(path == prefix or path.startswith(prefix + "/") for prefix in namespaces):
            path = "/" + scope + path
        if path.startswith("/"):
            relative = posixpath.normpath(path).lstrip("/")
        elif path:
            relative = posixpath.normpath((source.parent.relative_to(self.root) / path).as_posix())
        else:
            relative = source.relative_to(self.root).as_posix()
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            return target, unquote(parsed.fragment)
        if target.is_dir():
            target = target / "index.html"
        elif not target.is_file() and Path(str(target) + ".html").is_file():
            target = Path(str(target) + ".html")
        return target, unquote(parsed.fragment)

    def check(self, url, source, scope=None):
        resolved = self.resolve(url, source, scope)
        if resolved is None:
            return
        self.count += 1
        target, fragment = resolved
        location = source.relative_to(self.root).as_posix()
        if not target.is_relative_to(self.root) or not target.is_file():
            self.errors.append(f"{location}: missing target {url}")
            return
        if fragment and target.suffix == ".html":
            anchors = self.html(target).anchors
            relative = target.relative_to(self.root)
            # DocC creates anchors in the client from render data instead of the HTML shell.
            if len(relative.parts) > 2 and relative.parts[1] in {"documentation", "tutorials"}:
                data = self.root / relative.parts[0] / "data" / (Path(*relative.parts[1:-1]).as_posix() + ".json")
                if data.is_file():
                    anchors = anchors | json_anchors(json.loads(data.read_text()))
            if fragment not in anchors:
                self.errors.append(f"{location}: missing anchor {url}")

    def scan(self):
        for source in sorted(self.root.rglob("*.html")):
            for url in self.html(source).links:
                self.check(url, source)
        for source in sorted(self.root.rglob("*.css")):
            for url in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", source.read_text()):
                self.check(url.strip(), source)
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or not (directory / "data").is_dir():
                continue
            for source in sorted((directory / "data").rglob("*.json")):
                value = json.loads(source.read_text())
                for reference in value.get("references", {}).values():
                    if isinstance(reference.get("url"), str):
                        self.check(reference["url"], source, directory.name)
                    for variant in reference.get("variants", []):
                        if isinstance(variant.get("url"), str):
                            self.check(variant["url"], source, directory.name)
        return self.errors
