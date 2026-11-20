# Case study for issue #1

The default branch described a Swift template, and it contained no runnable example or CI. The project needs both the pipeline and enough evidence for downstream maintainers to decide how to adopt it. The UI pilot adds an important constraint. Its published root manifest already serves SwiftPM consumers, while its parser, renderer and specification fixtures live in separate directories. [Collected evidence](evidence.md)

## Requirements

| Issue requirement | Solution plan and verification |
| --- | --- |
| Use the same or similar practices throughout Hive Mind's guide | Translate each of the 17 principles into a Swift-specific check or publishing operation, as mapped below. Verify Linux and macOS qualification, workflow syntax and security, and release behavior in a temporary Git remote. |
| Create a reusable template designed for Swift | Ship a dependency-free SwiftPM package with a CLI and Swift Testing tests. Provide template and embedded modes, with a versioned toolchain and a monorepo caller. Verify that a docs-only or unrelated-language edit skips the Swift build while changes to shared test fixtures trigger it. |
| Report to Hive Mind and ask it to update the docs | File a linked adoption issue covering the localized documentation, the `fix --ci-cd` Swift mapping, and the inventory tests. Verify the issue URL in PR #2. |
| Report to UI and ask it to apply the template in `./swift` in multi-language mode | File a linked adoption issue with steps to install the reusable lane in `./swift`, keep the SwiftPM root, preserve the other languages, and carry forward its SwiftUI demo and screenshot checks. Verify the issue URL in PR #2. |
| Collect repository data and research online | Capture the timeline, source revisions, downstream starting point and official references in this folder. |
| Analyze the case deeply and compare existing tools and implementation plans | Record the trade-offs and source mapping below. Tie the chosen options to repeatable verification. |
| Execute this work in one PR | Update the prepared PR with the implementation and research, a closing reference to issue #1, and links to the two adoption reports. |

## Alternatives

| Area | Options considered and decision |
| --- | --- |
| Swift build and lint | [SwiftPM](https://docs.swift.org/swiftpm/documentation/packagemanagerdocs/) and the bundled [swift-format](https://github.com/swiftlang/swift-format) cover a dependency-free baseline on Linux and macOS. [SwiftLint](https://github.com/realm/SwiftLint) adds configurable style and analyzer rules at the cost of another pinned installation and platform considerations. Strict formatter lint plus compiler warnings as errors is the default. Xcode-based app and simulator workflows remain a project choice. |
| Tools and runner consistency | Pin OS labels and the exact Swift toolchain. [try! Swift Setup](https://github.com/tryswift/setup-swift) can reuse an exact match from a hosted image and otherwise verifies the Swift.org distribution. Docker tool and base images reference immutable digests. |
| Release delivery | [SwiftPM's source-control versions](https://docs.swift.org/swiftpm/documentation/packagemanagerdocs/addingdependencies/) work for packages hosted on GitHub without a registry account. A [Swift package registry](https://docs.swift.org/swiftpm/documentation/packagemanagerdocs/packageregistry/) adds an identity namespace, signing and organization-specific credentials. Use Git tags and GitHub Releases for the portable default. |
| Changelog tooling | A commit-message parser such as [Release Please](https://github.com/googleapis/release-please) can infer semantic versions and open release PRs. One file per change supports review and yields a meaningful changelog even with varied commit conventions. A small Python generator implements the guide's direct, metadata-only version commit. |
| Vulnerability checks | A PR dependency-review gate only sees changed dependencies. OSV can scan the full committed SwiftPM pin set on changes and weekly, catching newly disclosed advisories on older pins. Dependabot handles updates where the manifest has dependencies. |
| Container publication | Native, parallel OCI builds avoid emulation. Transfer their artifacts to a single serialized writer, then assemble and verify the OCI index. Keep the GHCR mirror optional for library-only projects. |
| Scope and reproducibility | Workflow-level path filters save runs but can leave required status checks pending. Classify the complete Git diff inside an always-triggered check and validate the current merge. Keep the shared scaffold in a copyable directory so a monorepo can supply repository-relative package and fixture paths. |

## Guide mapping

| Hive Mind principle | Swift implementation and evidence |
| --- | --- |
| 1. Relevant change detection | `scope.py` classifies the actual Git diff into Swift, docs, workflow and container scopes. Tests cover docs-only, workflow-only, Docker-only and mixed-language fixture edits. |
| 2. File size | `check_swift.py` applies the 1,500-line policy to staged or tracked files, and `docs.py` caps Markdown at 2,500. |
| 3. Automated formatting | Toolchain `swift format`, repo configuration and the shared local formatting command. |
| 4. Static analysis | `swift format lint --strict` plus warnings-as-errors when compiling code and test targets on Ubuntu and macOS. |
| 5. Fast feedback | Detection, secrets, formatting, docs, workflow checks and dependency analysis precede the Linux/macOS test matrix. Compile tests once and execute with `--skip-build`. |
| 6. Changesets | Per-PR fragments, a maximum semantic bump, a generated changelog and guardrails for generated version files. Tests cover docs-only edits, existing fragments and version bumps. |
| 7. Actual merge | Check out the GitHub merge preview and merge the newest base SHA once per run. All checking jobs use that base. Test the queue's merge group commit when present. |
| 8. Pre-commit hook | Staged Swift lint and line count use the index, including staged formatter configuration. Gitleaks checks staged content with redacted output. |
| 9. Release automation | Default-branch and manual runs use the Actions token to publish an atomic metadata commit and SwiftPM tag. Recover a missing GitHub Release by reading the tag's changelog. A separate job verifies the public tag and GitHub Release anonymously. |
| 10. Concurrency | Scope cancellation to read-only checks. Serialize publishing jobs, classify ref-policy denials separately, retry bounded races and recompute metadata without publishing untested source. |
| 11. Secrets detection | Gitleaks scans introduced commits so a later deletion in the same PR cannot hide the earlier leak from CI. |
| 12. Documentation validation | Required headings, size checks and Lychee local-link validation catch deterministic repository errors. A weekly report checks external URLs and identifies upstream failures without blocking a source release. |
| 13. Native multi-arch containers | Native amd64/arm64 matrix, per-architecture caches, smoke tests, digest-based OCI manifest and read-back verification with an anonymous token. Source releases complete before the optional mirror. |
| 14. Workflow lint | Actionlint's image includes ShellCheck. Zizmor emits medium-confidence-or-higher annotations without SARIF upload. |
| 15. Dependency audit | Scan committed SwiftPM pins with OSV on Swift changes and weekly. Fail for any reported advisory. Require a tracked lockfile as soon as the package resolves external dependencies. |
| 16. Release preflight | A GitHub Git-object write probes token permissions and the package archive is measured before qualification. GHCR opens and cancels an empty upload session before OCI builds. Git ref rules are enforced by the actual atomic push, and first-use image visibility is verified separately. |
| 17. External state | Explicit time limits and status notices. A rejected ruleset write explains the policy and avoids redundant retries. A stalled write can retry without creating another version. The dependency schedule checks advisories independently of source changes, and ecosystem configuration covers the files that exist. |

## Verification

Run the local checks from the repository root.

```sh
python3 -m unittest discover -s experiments -p 'test_*.py' -v
python3 swift/ci/check_swift.py
python3 swift/ci/docs.py standalone swift/ci
SWIFT_PACKAGE=. bash swift/ci/test-package.sh
```

The Linux pilot used UI's actual root package, specification fixtures and renderer sources at [revision 5a7de31](https://github.com/link-foundation/ui/tree/5a7de318166319a0847c9a339fe836c8843b4588). Its 33 XCTest cases passed when run through the template's package test step. See the [monorepo guide](../../monorepo.md) for the proposed scopes.

The release test uses a disposable bare Git remote. It exercises the actual atomic Git push, simulates a failed GitHub Release request, retries, and asserts that the original tag is recovered. Registry tests use HTTP fixtures for the upload probe and both-architecture verification. The live release workflow only publishes from `main`. Its GitHub and GHCR write paths run after merge with the repository's Actions token. Hosted test and optional native container results are recorded on [PR #2](https://github.com/link-foundation/swift-ai-driven-development-pipeline-template/pull/2/checks).
