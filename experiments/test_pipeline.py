"""Focused checks for CI scope, generated metadata and release recovery."""

from contextlib import contextmanager, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "swift/ci"))

import metadata
import registry
import release
from scope import classify

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


@contextmanager
def repository():
    with tempfile.TemporaryDirectory() as directory:
        original = Path.cwd()
        os.chdir(directory)
        try:
            metadata.git("init", "-b", "main")
            metadata.git("config", "user.name", "Test")
            metadata.git("config", "user.email", "test@example.invalid")
            metadata.VERSION_FILE.parent.mkdir(parents=True)
            metadata.VERSION_FILE.write_text("0.0.0\n")
            metadata.CHANGELOG.write_text("# Changelog\n\nInitial notes.\n")
            metadata.CHANGESETS.mkdir()
            Path("Package.swift").write_text("// Swift package fixture\n")
            metadata.git("add", ".")
            metadata.git("commit", "-m", "Fixture")
            yield Path(directory)
        finally:
            os.chdir(original)


def changeset(name, contents):
    path = metadata.CHANGESETS / name
    path.write_text(contents, encoding="utf-8")
    metadata.git("add", path)
    metadata.git("commit", "-m", name)


class ScopeTests(unittest.TestCase):
    def test_docs_only_skips_swift_and_containers(self):
        result = classify(["README.md", "docs/research.md"], ["."], "swift/ci", True)
        self.assertEqual(result, dict(code=False, swift=False, docs=True, workflows=False, container=False))

    def test_pipeline_changes_recheck_the_pipeline(self):
        result = classify(["swift/ci/release.py", ".github/workflows/swift-ci.yml"], ["."], "swift/ci", True)
        self.assertFalse(result["code"])
        self.assertTrue(result["swift"])
        self.assertTrue(result["workflows"])

    def test_embedded_scope_preserves_cross_language_fixtures(self):
        paths = ["Package.swift", "packages/ui-swift", "docs/spec"]
        self.assertFalse(classify(["package-lock.json"], paths, "swift/ci", False)["swift"])
        self.assertTrue(classify(["docs/spec/fixture.md"], paths, "swift/ci", False)["swift"])
        self.assertFalse(classify(["packages/ui-swift/Sources/F.swift"], paths, "swift/ci", False)["container"])

    def test_docker_edit_runs_container_without_swift_rebuild(self):
        result = classify(["Dockerfile"], ["."], "swift/ci", True)
        self.assertTrue(result["container"])
        self.assertFalse(result["swift"])


class MetadataTests(unittest.TestCase):
    def test_changeset_must_be_new_to_pull_request(self):
        with repository():
            changeset("existing.md", "minor\nAlready included\n")
            base = metadata.git("rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "Add a new changeset"):
                metadata.validate_pull_request(base, True)
            metadata.validate_pull_request(base, False)
            changeset("added.md", "patch\nNew change\n")
            metadata.validate_pull_request(base, True)
            metadata.validate_pull_request(EMPTY_TREE, True)

    def test_generated_version_cannot_be_edited(self):
        with repository():
            base = metadata.git("rev-parse", "HEAD")
            metadata.VERSION_FILE.write_text("7.0.0\n")
            metadata.git("add", metadata.VERSION_FILE)
            metadata.git("commit", "-m", "Manual version")
            with self.assertRaisesRegex(ValueError, "Generated files changed"):
                metadata.validate_pull_request(base, False)

    def test_highest_bump_consumes_entries_and_keeps_historical_notes(self):
        with repository():
            changeset("feature.md", "minor\nA feature\n")
            changeset("fix.md", "patch\nA fix\n")
            entries = metadata.read_changesets()
            self.assertEqual(metadata.next_version("1.9.3", entries), "1.10.0")
            metadata.advance("1.10.0", entries)
            metadata.git("commit", "-m", "Release")
            metadata.git("tag", "v1.10.0")
            self.assertEqual(metadata.version(), "1.10.0")
            self.assertEqual(metadata.read_changesets(), [])
            self.assertEqual(metadata.notes_for_tag("v1.10.0"), "## [1.10.0]\n\n- A feature\n- A fix\n")


class ReleaseTests(unittest.TestCase):
    def test_rule_rejection_takes_priority_over_race(self):
        self.assertEqual(release.classify_push("GH013: rules\n[rejected] (fetch first)"), "rule")
        self.assertEqual(release.classify_push("[rejected] (non-fast-forward)"), "race")
        self.assertEqual(release.classify_push("Connection reset by peer"), "unknown")

    def test_only_release_metadata_can_be_recomputed_without_retesting(self):
        with repository():
            validated = metadata.git("rev-parse", "HEAD")
            changeset("feature.md", "minor\nFeature\n")
            self.assertFalse(release.head_has_changed(validated, "HEAD"))
            Path("Package.swift").write_text("// New untested source\n")
            metadata.git("commit", "-am", "Update source")
            self.assertTrue(release.head_has_changed(validated, "HEAD"))

    def test_atomic_push_and_interrupted_github_release_are_recoverable(self):
        with tempfile.TemporaryDirectory() as server, repository() as work:
            remote = Path(server, "remote.git")
            subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
            changeset("feature.md", "minor\nFeature\n")
            anchor = metadata.git("rev-parse", "HEAD")
            metadata.git("remote", "add", "origin", remote)
            metadata.git("push", "origin", "main")
            out = work / "output"
            with patch.dict(os.environ, GITHUB_OUTPUT=str(out)), patch.object(release, "available_releases", return_value={}):
                with patch.object(release, "publish_release", side_effect=ValueError("Simulated API failure")):
                    with self.assertRaisesRegex(ValueError, "Simulated API failure"):
                        release.publish(anchor, "main")
                self.assertEqual(metadata.git("ls-remote", "--tags", "origin").split()[1], "refs/tags/v0.1.0")
                self.assertEqual(metadata.git("ls-remote", "--heads", "origin").split()[0],
                                 metadata.git("rev-parse", "v0.1.0"))
                with patch.object(release, "publish_release") as repair:
                    release.publish(anchor, "main")
                    repair.assert_called_once_with("v0.1.0")
                self.assertIn("version=v0.1.0", out.read_text())


class RegistryTests(unittest.TestCase):
    def test_write_probe_cancels_empty_upload(self):
        with patch.object(registry, "token", return_value="fixture"), patch.object(
            registry, "request", side_effect=[
                (202, "/v2/owner/name/blobs/uploads/upload-id", b""),
                (204, None, b""),
            ]
        ) as request:
            registry.probe("owner/name")
            self.assertEqual([call.args[0] for call in request.call_args_list], ["POST", "DELETE"])

    def test_write_probe_rejects_location_on_another_host(self):
        with patch.object(registry, "token", return_value="fixture"), patch.object(
            registry, "request", return_value=(202, "https://other.invalid/upload", b"")
        ) as request:
            with self.assertRaisesRegex(ValueError, "unexpected upload location"):
                registry.probe("owner/name")
            request.assert_called_once()

    def test_prepare_stops_if_a_private_image_already_exists(self):
        with patch.object(registry, "platforms", side_effect=[None, {"linux/amd64"}]), patch.object(
            registry, "probe"
        ) as probe:
            with self.assertRaisesRegex(ValueError, "Make the GHCR package public"):
                registry.prepare("owner/name", "v1.0.0")
            probe.assert_not_called()

    def test_prepare_stops_if_registry_state_is_unknown(self):
        with patch.object(registry, "platforms", side_effect=registry.RegistryError("manifest read", 503)), patch.object(
            registry, "probe"
        ) as probe:
            with self.assertRaisesRegex(ValueError, "unknown"):
                registry.prepare("owner/name", "v1.0.0")
            probe.assert_not_called()

    def test_verify_requires_both_native_architectures(self):
        with patch.object(registry.time, "sleep"), redirect_stdout(io.StringIO()):
            with patch.object(registry, "platforms", return_value={"linux/amd64"}):
                with self.assertRaisesRegex(ValueError, "could not be verified anonymously"):
                    registry.verify("owner/name", "v1.0.0")
            with patch.object(registry, "platforms", return_value={"linux/amd64", "linux/arm64"}):
                registry.verify("owner/name", "v1.0.0")


if __name__ == "__main__":
    unittest.main()
