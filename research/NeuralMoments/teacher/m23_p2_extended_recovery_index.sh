#!/usr/bin/env bash
# W2 M23-P2: read-only broad index of possible Noodles V7 archives/backend.
# No file bytes are modified; no CSG/Cherchi is executed.
set -Eeuo pipefail
export LC_ALL=C

ROOT="${1:-/data}"
OUTPUT="${2:-$HOME/下载/W2_M23_P2_EXTENDED_RECOVERY_INDEX.tar.gz}"
[[ -d "$ROOT" ]] || { echo "ROOT_NOT_FOUND: $ROOT" >&2; exit 2; }
command -v find >/dev/null
command -v tar >/dev/null
command -v sha256sum >/dev/null

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp"
: > "$tmp/SCAN_ERRORS.txt"

# Exact filenames remain important; the file list is NOT the file bytes.
find "$ROOT" -type f \( \
    -name 'design-rational.json' -o \
    -name 'envelope-rational.json' -o \
    -name 'fixed-rational.json' -o \
    -name 'fixed-inside-envelope-rational.json' -o \
    -name 'fixed-outside-envelope-rational.json' -o \
    -name 'initial-rational.json' \
    \) -printf '%p\t%s\n' 2>>"$tmp/SCAN_ERRORS.txt" \
    | sort -u > "$tmp/EXACT_NAME_CANDIDATES.tsv" || true

# Broaden *archive extension*, not content reconstruction. List all candidate
# archive names, because a relevant archive may not contain "noodles" or "v7".
find "$ROOT" -type f \( \
    -iname '*.zip' -o -iname '*.tar' -o -iname '*.tar.gz' -o \
    -iname '*.tgz' -o -iname '*.tar.zst' -o -iname '*.zst' -o \
    -iname '*.tar.xz' -o -iname '*.tar.bz2' -o -iname '*.7z' -o \
    -iname '*.rar' -o -iname '*.xz' -o -iname '*.json.gz' \
    \) -printf '%p\t%s\n' 2>>"$tmp/SCAN_ERRORS.txt" \
    | sort -u > "$tmp/ARCHIVE_CANDIDATES.tsv" || true

# CGAL/Boolean binary filenames can differ from "noodles-exact-boolean".
find "$ROOT" -type f \( \
    -iname '*boolean*' -o -iname '*cgal*' -o \
    -iname '*rational*backend*' -o -iname '*exact*mesh*' \
    \) -printf '%p\t%s\n' 2>>"$tmp/SCAN_ERRORS.txt" \
    | sort -u > "$tmp/BOOLEAN_BACKEND_CANDIDATES.tsv" || true

find "$ROOT" -type d \( \
    -iname '*noodles*' -o -iname '*exact_v7*' -o \
    -iname '*cgal*' \
    \) -print 2>>"$tmp/SCAN_ERRORS.txt" \
    | sort -u > "$tmp/RELATED_DIRECTORIES.txt" || true

{
    printf 'W2 M23-P2 extended recovery inventory (READ ONLY)\n'
    printf 'SEARCH_ROOT=%s\n' "$ROOT"
    printf 'NOTE=No archive contents were inspected, no SHA for candidate payloads was independently checked.\n'
    printf 'NOTE=No CGAL/Cherchi execution or mutation. Lists can include unrelated files.\n'
    printf 'EXACT_NAME_CANDIDATES=%s\n' "$(wc -l < "$tmp/EXACT_NAME_CANDIDATES.tsv")"
    printf 'ARCHIVE_CANDIDATES=%s\n' "$(wc -l < "$tmp/ARCHIVE_CANDIDATES.tsv")"
    printf 'BOOLEAN_BACKEND_CANDIDATES=%s\n' "$(wc -l < "$tmp/BOOLEAN_BACKEND_CANDIDATES.tsv")"
    printf 'RELATED_DIRECTORIES=%s\n' "$(wc -l < "$tmp/RELATED_DIRECTORIES.txt")"
    printf 'SCAN_ERROR_LINES=%s\n' "$(wc -l < "$tmp/SCAN_ERRORS.txt")"
} > "$tmp/README.txt"

mkdir -p "$(dirname "$OUTPUT")"
[[ ! -e "$OUTPUT" ]] || { echo "REFUSE_OVERWRITE: $OUTPUT" >&2; exit 3; }
tar -czf "$OUTPUT" -C "$tmp" .
echo "===== W2 M23-P2 extended recovery inventory ====="
cat "$tmp/README.txt"
sha256sum "$OUTPUT"
echo "REPORT_PACKAGE=$OUTPUT"
