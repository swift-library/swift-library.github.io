#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
"""Shared inputs for the catalog, documentation builder, and site checks."""

import base64
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


class SiteError(RuntimeError):
    pass


def configuration():
    config = json.loads((ROOT / "projects.json").read_text())
    repositories = [p["repository"] for g in config["groups"] for p in g["projects"]]
    if len(repositories) != len(set(repositories)):
        raise SiteError("projects.json contains duplicate repositories")
    for project in projects(config):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", project["repository"]):
            raise SiteError("Invalid repository name")
        if project["documentation"]["kind"] not in {"docc", "readme"}:
            raise SiteError("Invalid documentation kind")
    return config


def projects(config):
    return [project for group in config["groups"] for project in group["projects"]]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


class GitHub:
    def __init__(self):
        self.token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"], capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    self.token = result.stdout.strip()
            except FileNotFoundError:
                pass

    def get(self, endpoint, missing=False):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "swift-library-site",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = Request("https://api.github.com/" + endpoint, headers=headers)
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response), response.headers
        except HTTPError as error:
            if missing and error.code == 404:
                return None, {}
            raise SiteError(f"GitHub API {endpoint}: HTTP {error.code}") from None
        except URLError as error:
            raise SiteError(f"GitHub API {endpoint}: {error.reason}") from None

    def pages(self, endpoint):
        page = 1
        while True:
            separator = "&" if "?" in endpoint else "?"
            values, headers = self.get(f"{endpoint}{separator}per_page=100&page={page}")
            if not isinstance(values, list):
                raise SiteError(f"GitHub API {endpoint}: expected a list")
            yield from values
            if 'rel="next"' not in headers.get("Link", ""):
                break
            page += 1

    def public_repositories(self, organization):
        return {
            repo["name"]: repo
            for repo in self.pages(f"orgs/{organization}/repos?type=public")
            if not repo["fork"] and not repo["private"]
        }

    def bytes_file(self, organization, repository, path, ref):
        endpoint = f"repos/{organization}/{repository}/contents/{quote(path)}?ref={quote(ref, safe='')}"
        value, _ = self.get(endpoint)
        if value.get("encoding") != "base64":
            raise SiteError(f"Expected file content for {repository}/{path}")
        return base64.b64decode(value["content"])

    def text_file(self, organization, repository, path, ref):
        return self.bytes_file(organization, repository, path, ref).decode("utf-8")


def latest_tag(api, organization, repository):
    tags = list(api.pages(f"repos/{organization}/{repository}/tags"))
    return tags[0] if tags else None


def latest_release(api, organization, repository):
    for release in api.pages(f"repos/{organization}/{repository}/releases"):
        if not release["draft"]:
            return release
    return None


def readme_url(api, organization, repo):
    value, _ = api.get(f"repos/{organization}/{repo['name']}/readme", missing=True)
    return value["html_url"] if value else repo["html_url"]


def contributor_names(api, organization, repositories):
    names = set()
    for repository in sorted(repositories):
        repo = repositories[repository]
        if repo["size"] == 0:
            continue
        endpoint = f"repos/{organization}/{repository}/commits?sha={quote(repo['default_branch'], safe='')}"
        for commit in api.pages(endpoint):
            account = commit.get("author") or {}
            author = commit["commit"].get("author") or {}
            name = " ".join((author.get("name") or account.get("login") or "").split())
            identity = " ".join([name, account.get("login", ""), author.get("email", "")])
            if account.get("type") == "Bot" or re.search(r"\[bot\]|\bbot\b", identity, re.I):
                continue
            if not name or "@" in name or "<" in name or ">" in name:
                continue
            names.add(name)
    return sorted(names, key=lambda value: (value.casefold(), value))


def write_contributors(path, names):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + "\n")
