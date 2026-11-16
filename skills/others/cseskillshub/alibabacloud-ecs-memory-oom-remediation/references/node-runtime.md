# Node.js runtime memory limit

The parameter wording follows the Node.js command-line documentation:
https://nodejs.org/api/cli.html#--max-old-space-sizesize-in-mib

## What the parameter means

- `--max-old-space-size` caps the V8 old-space heap in **MiB**. The default depends on
  the Node.js version, so the official document is the reference, not this file.
- It caps the V8 heap only. Buffer and ArrayBuffer allocations live outside the heap, so
  a process can exceed this number and still be memory-hungry.
- Too small a value increases garbage-collection pressure and can raise an
  out-of-memory error inside the process. Too large a value can hide a real leak.
  Start conservative and adjust after the verification run.

## Why the skill only advises

The parameter is read at process start, so it takes effect only after the business
process restarts. This skill does not change environment files, package scripts or
service units, and it does not restart anything: it reports the current value it found
and hands the customer the example command.

The collector returns one line per Node process:

```text
node_1=pid:2143|rss_kb:1443820|max_old_space_size:2048|args:node app.js
```

`max_old_space_size:not_set` means no explicit limit was found in the command line, so
the process runs with the version default.

## Launch variants (customer executes these)

Environment variable for the current user (affects every Node process of that user, so
state the blast radius before recommending it):

```bash
export NODE_OPTIONS="--max-old-space-size=2048"
```

npm script in `package.json`:

```json
"scripts": { "start": "node --max-old-space-size=2048 app.js" }
```

PM2 ecosystem file:

```js
module.exports = {
  apps: [{ name: "app", script: "app.js", node_args: "--max-old-space-size=2048" }]
}
```

systemd unit, appended to `ExecStart`:

```ini
ExecStart=/usr/bin/node --max-old-space-size=2048 /app/server.js
```

## Sizing principle

Leave enough memory for the operating system and for the other processes that were
identified as holders of resident memory in the same report. A limit that merely moves
the ceiling up does not solve an instance whose total demand exceeds its physical
memory: that case is Swap guidance plus an upgrade recommendation.