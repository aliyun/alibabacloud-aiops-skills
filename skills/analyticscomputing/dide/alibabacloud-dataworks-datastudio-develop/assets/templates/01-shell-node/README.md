# Example 01: Shell Node

The simplest DataWorks node example. Creates a Shell script node that runs daily at midnight.

## File Structure

```
hello/
├── hello.spec.json        # Node definition
├── hello.sh               # Shell script
└── dataworks.properties   # Configuration
```

## Creation Steps

1. Create a spec file based on hello/hello.spec.json
2. Modify name, path, and content
3. Write hello.sh
4. Create dataworks.properties
5. Git Mode: `git add && git commit`
6. OpenAPI Mode: Call CreateNode API directly with minSpec
