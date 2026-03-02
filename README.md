# bugsnag-dsym-sync

Stop hunting for Xcode archives and copy-pasting API keys. `bugsnag-dsym-sync` is a lightweight interactive tool that finds your recent builds and uploads their dSYMs to Bugsnag in seconds.

## Features

- **One-command sync** — upload all unuploaded archives across every project in the past 7 days with a single confirmation
- **Upload history** — tracks what's already been uploaded so you never double-submit
- **Smart archive discovery** — automatically scans your Xcode archives folder for builds in any date range you specify
- **Per-project API keys** — configure each Bugsnag project once, then forget about it
- **Format validation** — catches malformed API keys before they waste your time

## Requirements

- Python 3.9+
- [`bugsnag-dsym-upload`](https://docs.bugsnag.com/build-integrations/dsym/) on your PATH — the official Bugsnag CLI that does the actual uploading (`gem install bugsnag-dsym-upload`)

## Setup

```bash
curl -fsSL https://raw.githubusercontent.com/dennislysenko/bugsnag-dsym-sync/main/install.sh | bash
```

This clones the repo to `~/.local/share/bugsnag-dsym-sync`, sets up a virtual environment, and symlinks `bugsnag-dsym-sync` into `/usr/local/bin`. To update later, just run the same command again.

## Usage

```bash
bugsnag-dsym-sync           # interactive menu, 7-day window
bugsnag-dsym-sync -d 30     # look back 30 days
bugsnag-dsym-sync -s 2026-02-01 -e 2026-02-28   # explicit date range
```

On first launch, go to **Manage projects → Add project** to save your Bugsnag project API keys. Find keys at [app.bugsnag.com/settings](https://app.bugsnag.com/settings/) → Projects (left sidebar) → click your project.

After that, **Sync all projects (7d)** is all you need day-to-day.

## How it works

Archives are discovered from `~/Library/Developer/Xcode/Archives`. Each project has a configurable archive prefix (e.g. `MP3Converter`) that's matched against Xcode's archive folder names. Upload history is stored locally in `~/.config/bugsnag-dsym-sync/projects.json` — it only reflects uploads made from this machine, which is fine for a standard single-developer workflow.
