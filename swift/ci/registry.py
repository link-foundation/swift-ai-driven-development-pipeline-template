"""Probe GHCR writes and verify release images with an anonymous pull token."""

import argparse
import base64
from http.client import HTTPSConnection
import json
import os
import time
from urllib.parse import urlencode, urljoin, urlsplit

HOST = "ghcr.io"
INDEX_TYPES = "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"


def request(method, path, **headers):
    connection = HTTPSConnection(HOST, timeout=20)
    try:
        connection.request(method, path, headers=headers)
        response = connection.getresponse()
        return response.status, response.getheader("Location"), response.read()
    finally:
        connection.close()


def status_error(operation, status):
    reason = "denied" if status in (401, 403) else "unknown"
    raise ValueError(f"GHCR {operation}: {reason} (HTTP {status}).")


def token(image, push=False):
    headers = {}
    actions = "pull"
    if push:
        actions = "pull,push"
        credentials = f'{os.environ["GITHUB_ACTOR"]}:{os.environ["GH_TOKEN"]}'
        headers["Authorization"] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
    query = urlencode({"service": HOST, "scope": f"repository:{image}:{actions}"})
    status, _, body = request("GET", f"/token?{query}", **headers)
    if status != 200:
        status_error("token", status)
    return json.loads(body)["token"]


def probe(image):
    headers = {"Authorization": f"Bearer {token(image, push=True)}"}
    status, location, _ = request("POST", f"/v2/{image}/blobs/uploads/", **headers)
    if status != 202 or not location:
        status_error("upload authorization", status)
    url = urlsplit(urljoin(f"https://{HOST}", location))
    if url.scheme != "https" or url.netloc != HOST or not url.path.startswith(f"/v2/{image}/blobs/uploads/"):
        raise ValueError("GHCR returned an unexpected upload location.")
    status, _, _ = request("DELETE", f"{url.path}?{url.query}" if url.query else url.path, **headers)
    if status != 204:
        status_error("upload cleanup", status)
    print("GHCR accepted and cancelled an empty upload session.")


def platforms(image, version):
    status, _, body = request("GET", f"/v2/{image}/manifests/{version}",
                              Authorization=f"Bearer {token(image)}", Accept=INDEX_TYPES)
    if status != 200:
        status_error("anonymous manifest read", status)
    entries = json.loads(body).get("manifests", [])
    return {f'{p.get("os")}/{p.get("architecture")}' for entry in entries if (p := entry.get("platform"))}


def verify(image, version):
    for delay in (0, 2, 5, 15, 30):
        time.sleep(delay)
        try:
            actual = platforms(image, version)
            if {"linux/amd64", "linux/arm64"} <= actual:
                print(f"Anonymous manifest for {image}:{version} includes linux/amd64 and linux/arm64.")
                return
            cause = f"architectures found: {sorted(actual)}"
        except (OSError, ValueError, KeyError) as error:
            cause = str(error)
        print(cause, flush=True)
    raise ValueError("The image could not be verified anonymously. On first publication, make the GHCR package public.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["probe", "verify"])
    parser.add_argument("version", nargs="?")
    options = parser.parse_args()
    image = os.environ["GITHUB_REPOSITORY"].lower()
    try:
        if options.operation == "probe":
            probe(image)
        elif options.version:
            verify(image, options.version)
        else:
            parser.error("verify requires a version")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"::error::{error}\n")


if __name__ == "__main__":
    main()
