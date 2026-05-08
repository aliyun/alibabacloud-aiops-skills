# Introduction

DataWorks Data Integration supports using Stream Reader and Stream Writer plugins for bidirectional read and write capabilities through Stream. This article introduces the data read and write capabilities of DataWorks for Stream.

# Destination

## Parameter Description

No parameter description available.

## Configuration Example

```json
{
            "stepType":"stream",//Plugin name.
            "parameter":{
                "print":false,//Whether to print output to the screen.
                "fieldDelimiter":","//Column delimiter.
            },
            "name":"Writer",
            "category":"writer"
        }
```
