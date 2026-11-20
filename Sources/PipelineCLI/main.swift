import PipelineExample

print(greeting(for: CommandLine.arguments.dropFirst().first ?? "Swift"))
