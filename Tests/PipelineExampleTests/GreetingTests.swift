import PipelineExample
import Testing

@Test(arguments: ["Swift", "世界"])
func greetsName(name: String) {
  #expect(greeting(for: name) == "Hello, \(name)!")
}
