# Adopt the Swift pipeline in a multi-language repository

1. Copy `swift/ci/` to your repository's `./swift/ci/`.
2. Copy the reusable [.github/workflows/swift-ci.yml](../.github/workflows/swift-ci.yml). Add a caller at `.github/workflows/swift-checks.yml` similar to the following example.
3. Configure Swift file formatting for your project. Enable the [shared hook](../swift/ci/hooks/pre-commit) through your existing hooks if you want staged Swift formatting and secrets checks. Adapt its Git pathspecs to your Swift source directories.
4. Preserve any project-specific Swift steps, such as simulator tests, screenshot uploads, and test fixtures maintained in another language. Keep the repository's release workflow and version policy. Embedded mode supplies a read-only CI lane and leaves releases to the host repository.

```yaml
name: Swift Checks
on:
  pull_request:
  merge_group:
  push:
    branches: [main]
  schedule:
    - cron: '19 4 * * 1'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  swift:
    uses: ./.github/workflows/swift-ci.yml
    with:
      mode: embedded
      pipeline-directory: swift/ci
      package-directory: '.'
      source-paths: |
        Package.swift
        Package.resolved
        native/swift/LinksNotation
        packages/ui-swift
        examples/swift
        docs/spec
        docs/case-studies/issue-1/samples
```

Each source path is a repository-relative file or a directory prefix. Explicit Markdown under `docs/` can be a test input, as in this example. GitHub workflow and Swift formatter config changes also invalidate the Swift lane. The Linux/macOS test matrix builds the manifest in `package-directory`. For a second SwiftPM manifest, add another caller job with its own package directory and scope.

For [link-foundation/ui](https://github.com/link-foundation/ui), preserve the root SwiftPM URL and its products, adopt the reusable workflow for the root package and parser, and retain the current macOS SwiftUI demo and screenshot checks until the new jobs are validated. Keep JavaScript and Kotlin triggers and releases in their existing workflows. Use the scoped workflow as a merge gate after confirming it runs with the specification fixtures and that unrelated package changes skip Swift compilation.
