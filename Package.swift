// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "SwiftPipelineExample",
  products: [
    .library(name: "PipelineExample", targets: ["PipelineExample"]),
    .executable(name: "swift-pipeline-example", targets: ["PipelineCLI"]),
  ],
  targets: [
    .target(name: "PipelineExample"),
    .executableTarget(name: "PipelineCLI", dependencies: ["PipelineExample"]),
    .testTarget(name: "PipelineExampleTests", dependencies: ["PipelineExample"]),
  ]
)
