# Chrono Rift

This repository contains a simple Scratch 3 project builder that creates a playable `chrono-rift.sb3` archive.

## Build locally

Open a terminal in the repo and run:

```bash
python3 build_game.py
```

This generates:

```bash
chrono-rift.sb3
```

Then open Scratch and use:

- File → Load from your computer
- Select `chrono-rift.sb3`

## Build in GitHub Actions

The workflow in `.github/workflows/build-scratch.yml` runs automatically and uploads the generated `.sb3` as a downloadable artifact.

## Controls

- Arrow keys: move the ship
- Mouse button: shoot
- Goal: survive the rift and keep the score rising
