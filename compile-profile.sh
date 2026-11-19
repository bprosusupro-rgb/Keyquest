#!/usr/bin/env bash
set -euo pipefail
sdk="$(realpath "${1:?RenPy SDK directory}")"
profile="${2:?Engine family such as 8_4}"
project="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/game"
cp "$project/game/"*.rpy "$project/assets/"keyquest_*.png "$scratch/game/"
printf 'label start:\n    return\n' > "$scratch/game/script.rpy"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$sdk/renpy.sh" "$scratch" lint
"$sdk/renpy.sh" "$scratch" compile
cp "$scratch/game/keyquest_overlay.rpyc" "$project/assets/keyquest_$profile.rpyc"
cp "$scratch/game/keyquest_values.rpyc" "$project/assets/keyquest_values_$profile.rpyc"
cp "$scratch/game/keyquest_automation.rpyc" "$project/assets/keyquest_automation_$profile.rpyc"
