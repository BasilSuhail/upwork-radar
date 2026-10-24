# Upwork Radar (this fork's addition)

A paste-in job screener. Paste an Upwork job into a small web page; Claude Haiku scores it against your
profile (0-10, apply / maybe / skip, red flags) and drafts a proposal for the good ones. You read the
draft and send it on Upwork yourself.

It never logs in to Upwork, never scrapes and never submits anything. Upwork's terms forbid scraping and
automated proposals, and breaking them can get the account suspended.

The original UpworkScribe code (`main.py`, `src/`) is untouched; the radar lives in `radar/`.

## Needs

- Python 3.9+ (standard library only, no `pip install`).
- Claude Code (`claude`) installed and logged in on the machine. The radar runs `claude -p --model haiku`.

## Private data: `~/.upwork-radar/` (never in git)

| File | What |
|---|---|
| `profile.md` | Who you are, target niches, what to skip, proof points. The model only uses what is here. |
| `radar.db` | Every job you pasted, its score, the draft and its status (new / sent / ignored). |
| `radar.conf` | `RADAR_HOST`, `RADAR_PORT`, `GITEA_BACKUP_URL` (shell `KEY=value` lines). |

## Use

```bash
python3 -m radar serve                  # web page on RADAR_HOST:RADAR_PORT (default 127.0.0.1:8787)
python3 -m radar score job.txt          # same scoring from the terminal (or pipe the text in)
python3 -m radar history                # list scored jobs
python3 -m unittest discover tests      # tests (fake model, no Claude usage)
```

## Server (systemd user service)

```bash
git clone https://github.com/BasilSuhail/upwork-radar.git ~/upwork-radar
cp scripts/linux/upwork-radar* ~/.config/systemd/user/ && systemctl --user daemon-reload
systemctl --user enable --now upwork-radar.service
```

Set `RADAR_HOST` to the machine's Tailscale IP so the page is reachable from your own devices only.

## Where the code lives

- **GitHub** `BasilSuhail/upwork-radar`: fork of `AIXerum/Upwork-Auto-Jobs-Applier-using-AI`, code only.
  Public, so no personal data ever goes in the repo. `upstream` points at the original (push disabled);
  pull their changes with `git fetch upstream && git merge upstream/main`.
- **Gitea** (owner's server, private): every work branch plus branch `backup`, which holds one AES-256
  encrypted file with all of `~/.upwork-radar`, the repo `.env` and a `git bundle` of the whole repo
  (`main` included, since the protocol hook blocks pushing `main` directly).

## Backup and restore

```bash
scripts/backup_to_gitea.sh     # first run asks for a passphrase (write it down); later runs reuse it
systemctl --user enable --now upwork-radar-backup.timer   # daily 03:30 on the server, after the first run
scripts/restore.sh             # on a fresh machine, inside a clone of the Gitea repo
```
