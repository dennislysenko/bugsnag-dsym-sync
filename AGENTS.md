# bugsnag-upload

Interactive TUI wrapper for `bugsnag-dsym-upload`. Discovers Xcode archives in a configurable date window, tracks upload history locally, and supports syncing all projects at once.

## Location

```
/Users/dennis/dev/take-agency/bugsnag-upload/
├── bugsnag-upload.py   # Main script
├── requirements.txt    # questionary>=2.0, rich>=13.0
├── run.sh              # Launcher — auto-creates venv on first run
└── AGENTS.md           # This file
```

**Config file:** `~/.config/bugsnag-upload/projects.json`

## Running

```bash
./run.sh              # 7-day default
./run.sh -d 30        # last 30 days
./run.sh -s 2026-02-01 -e 2026-02-28
```

`run.sh` creates `venv/` and installs deps on first run, then invokes the script.

## Config Format

```json
{
  "projects": {
    "Transcribe": {
      "api_key": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
      "archive_prefix": "Transcribe"
    },
    "MP3 Converter": {
      "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "archive_prefix": "MP3Converter"
    }
  },
  "uploaded": [
    "Transcribe 2-28-26, 1.05 PM.xcarchive",
    "MP3Converter 2-27-26, 3.22 PM.xcarchive"
  ]
}
```

- **`api_key`** — Bugsnag project API key (32 lowercase hex chars). One per Bugsnag project — not shared across projects even on the same org account. Find it at https://app.bugsnag.com/settings/ → Projects (left sidebar) → click your project.
- **`archive_prefix`** — The string the `.xcarchive` folder name starts with. Decoupled from display name so e.g. "MP3 Converter" (display) → "MP3Converter" (prefix). Defaults to display name with spaces stripped.
- **`uploaded`** — Flat list of archive folder names recorded after a successful upload. **Local to this machine only** — archives uploaded from another machine won't appear here.

### Backwards compatibility

Old flat format (`"ProjectName": "api_key_string"`) is auto-migrated to the nested format on first load. Migration writes back to disk immediately.

## Archive Discovery

Archives live at:
```
~/Library/Developer/Xcode/Archives/YYYY-MM-DD/<archive_prefix>*.xcarchive
```

Discovery iterates date-named subdirectories within the date window and matches on `archive.name.startswith(archive_prefix)`.

## Upload History

Upload history tracks **archive folder names** (e.g. `Transcribe 2-28-26, 1.05 PM.xcarchive`). This is sufficient as a unique key since Xcode embeds a timestamp in the name.

- History is updated immediately after each successful upload (not batched at the end).
- Failed uploads are **not** recorded — they stay pending and will appear in future syncs.
- Users can still manually select and re-upload already-recorded archives via the single-project flow.

## Main Menu Options

1. **Sync all projects (7d)** — scans every project for unuploaded archives in the current date window, shows a summary table, and uploads all with one confirmation. This is the primary day-to-day action.
2. **Upload archives** — single-project flow with date range customisation and individual archive selection. Already-uploaded archives are shown with `[uploaded]` and pre-unchecked.
3. **Manage projects** — add/remove/list projects. Add prompts for display name, archive prefix (default: display name minus spaces), and API key (format-validated as 32 hex chars before saving).

## API Key Validation

Format-only check (`^[0-9a-f]{32}$`). Re-prompts on failure. No network call — the Bugsnag build API returns 400 for any non-empty string so cannot be used to distinguish valid from invalid keys.

## Dependencies

- `questionary` — interactive prompts (select, checkbox, text, confirm)
- `rich` — console output, tables, status spinners
- stdlib only for core logic (`subprocess`, `pathlib`, `json`, `datetime`, `re`, `argparse`)
