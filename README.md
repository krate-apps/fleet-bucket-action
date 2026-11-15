# fleet-bucket-action

Reusable GitHub Actions for **Fleet buckets**.

Canonical scripts live here. Bucket repos (Official, community, `fleet-template-bucket`) should call these actions instead of vendoring Python.

Published name (when remotes exist): [`krate-apps/fleet-bucket-action`](https://github.com/krate-apps/fleet-bucket-action).

## Actions

| Action                              | Role                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| [`validate`](validate/action.yml)   | `bucket.json` + `bucket/*.json` required fields, path existence, hash format, pinned GitHub URLs |
| [`hashcheck`](hashcheck/action.yml) | Download `architecture.*.url` and verify sha256                                                  |
| [`excavate`](excavate/action.yml)   | Bump listings from `checkver` / `autoupdate` (also fills missing `architecture` url/hash), then one commit per bump (+ optional push) |
| [`pin`](pin/action.yml)             | Apply `SHA256SUMS` → `architecture.linux-amd64` hash (+ url from release tag)                    |

## Usage in a bucket repo

```yaml
# .github/workflows/ci.yml
- uses: actions/checkout@v7
- uses: krate-apps/fleet-bucket-action/validate@v1
  with:
    path: .
```

```yaml
# .github/workflows/hashcheck.yml
- uses: actions/checkout@v7
- uses: krate-apps/fleet-bucket-action/hashcheck@v1
```

```yaml
# .github/workflows/excavator.yml
# permissions: contents: write
- uses: actions/checkout@v7
- uses: krate-apps/fleet-bucket-action/excavate@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    git-name: ${{ secrets.GIT_NAME }}
    git-email: ${{ secrets.GIT_EMAIL }}
```

```yaml
# Pin hashes after an extension/theme release (SHA256SUMS artifact or checkout path)
- uses: krate-apps/fleet-bucket-action/pin@v1
  with:
    path: .
    sums: ./SHA256SUMS
    tag: v1.2.3
```

`pin` sets `architecture.linux-amd64.hash` for each listing whose `{id}-linux-amd64.tar.gz` appears in the sums file. With `tag`, it also sets `url` to `https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>` using `checkver.github`, else a GitHub `homepage` / `source.repository`.

Excavate commits are `<id>: Update to version <ver>` (one per changed listing). Pass `git-name` / `git-email` from repo secrets; set `dry-run: true` to skip writes/commits, or `push: false` to commit locally only.

Pin a release tag (`@v1`) once the action repo is tagged; use `@main` only while bootstrapping.

## Local (workspace)

From a bucket checkout, with this tree beside `buckets/` / `templates/`:

```bash
FLEET_BUCKET_ROOT=. python3 ../../actions/fleet-bucket-action/scripts/validate-listings.py

FLEET_BUCKET_ROOT=. PIN_SUMS=/path/to/SHA256SUMS PIN_TAG=v1.2.3 \
  python3 ../../actions/fleet-bucket-action/scripts/pin-listings.py
```

Or pass the bucket root as argv: `python3 …/validate-listings.py /path/to/bucket-repo`.

## Inputs

| Input          | Default        | Used by                                |
| -------------- | -------------- | -------------------------------------- |
| `path`         | `.`            | all                                    |
| `github-token` | `github.token` | excavate                               |
| `dry-run`      | `false`        | excavate, pin                          |
| `git-name`     | _(empty)_      | excavate (required if listings change) |
| `git-email`    | _(empty)_      | excavate (required if listings change) |
| `push`         | `true`         | excavate                               |
| `sums`         | _(required)_   | pin                                    |
| `tag`          | _(empty)_      | pin (required to write urls)           |

## Tests

```bash
make test   # python3 unittest under tests/
```

CI runs on push to `main`/`develop` and on PRs targeting `main`.

## License

MIT

---

<p align="center">
  Developed by the <a href="https://runkrate.com">Krate</a> team.<br />
  Released under the MIT License.
</p>
