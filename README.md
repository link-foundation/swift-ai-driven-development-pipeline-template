# Swift AI-driven development pipeline template

This template ships a dependency-free SwiftPM library and CLI with Linux and macOS CI. The pipeline validates pull request merge results, then turns changesets into SwiftPM tags and GitHub Releases on `main`. An optional OCI mirror publishes a Linux CLI for amd64 and arm64.

## Getting started

1. Create a repository from this template and keep its default branch named `main`. Rename the sample products and targets in [Package.swift](Package.swift).
2. Install [Swift 6.4.1](https://www.swift.org/install/), Python 3 and [Gitleaks](https://github.com/gitleaks/gitleaks). Enable the shared pre-commit hook with `git config core.hooksPath swift/ci/hooks`.
3. Run the same checks locally before opening a pull request.

```sh
python3 swift/ci/check_swift.py --format
python3 swift/ci/check_swift.py
SWIFT_PACKAGE=. bash swift/ci/test-package.sh
swift run swift-pipeline-example CI
```

The hook lints staged Swift and checks staged contents for secrets. The formatting command updates tracked Swift files in your working tree. Stage the formatted changes before committing. The CI policy caps Swift files at 1,500 lines and Markdown at 2,500 lines. Swift compiles with compiler warnings treated as errors. If you introduce dependencies, check in `Package.resolved` and add Swift to [.github/dependabot.yml](.github/dependabot.yml). CI builds from the committed pins, and the weekly OSV scan also checks them when there are no new commits. A weekly link report checks public documentation URLs for upstream failures.

In repository rulesets, require the final **Swift pipeline status** check from the Swift Checks workflow and require branches to be up to date before merging, or enable a merge queue. The workflow runs for every PR and reports skipped work through its status check. CI scans introduced commits for secrets, tests the merge against the current base snapshot, and runs compilation and tests after smaller checks pass. Merge queue runs check the actual queued merge SHA. PR workflows use read-only permissions and support forks.

## Release

Add a [changeset](swift/ci/changesets/README.md) for Swift source or package changes. Documentation-only PRs can skip the changeset. A push to `main` with pending changesets builds and tests the tree and publishes the highest semantic-version bump. The initial changeset produces `v0.1.0`. GitHub's job token authorizes publishing. Configure the branch and tag rulesets so GitHub Actions can atomically push the generated release commit and its tag. A policy rejection fails with the original Git error and an instruction for the repository owner. A write probe verifies the token before the builds, and the atomic push enforces the branch and tag rules.

Run the **Swift Release** workflow on `main` to retry. It uses the same qualification checks. If a tag landed but its GitHub Release is missing, the workflow restores the Release from its tagged changelog. A writer that races another metadata update recomputes the version against the new tip. A newer source tree must pass its own CI run. Consumers install the package via the Git repository and a semantic-version constraint.

Set `ENABLE_SWIFT_IMAGE_CHECKS=true` in Actions variables to smoke-test native OCI builds in PRs and merge queue runs. Set `ENABLE_SWIFT_IMAGES=true` to mirror the GitHub Release to `ghcr.io/<owner>/<repo>:<tag>`. Set both if you intend to ship images. The workflow probes registry writes before native builds, uses per-architecture caches, tests the actual executable and assembles a multi-platform index from the two image digests. For the first GHCR publication, make the package public when verifying anonymous access. Rerun **Swift Release** to finish or verify that mirror. Pass `image-version` to retry a specific published version. Source package releases can succeed independently of the mirror.

## Monorepo adoption

Keep the Swift pipeline assets under `./swift` and use a small repository-level caller. SwiftPM can continue resolving a root manifest for consumers. See the [copy and configuration steps](docs/monorepo.md), including the proposed migration for `link-foundation/ui`.

The [issue #1 case study](docs/case-studies/issue-1/README.md) maps the requirements and Hive Mind practices to implementation and verification.
