#!/bin/zsh

set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
skill_parent_dir="${repo_root}/skills"
skill_name="scratch-blocks"

if (( $# < 1 || $# > 2 )); then
  echo "usage: $0 <version> [skill-name]" >&2
  echo "example: $0 v0.0.2 scratch-blocks-color" >&2
  exit 1
fi

version="$1"
if (( $# == 2 )); then
  skill_name="$2"
fi

if [[ ! "$version" =~ '^v[0-9]+(\.[0-9]+)*$' ]]; then
  echo "error: version must look like v0.0.2" >&2
  exit 1
fi

output_path="${repo_root}/dist/${skill_name}-${version}.zip"
skill_dir="${skill_parent_dir}/${skill_name}"

if ! command -v zip >/dev/null 2>&1; then
  echo "error: zip is required but was not found in PATH" >&2
  exit 1
fi

if [[ ! -d "$skill_dir" ]]; then
  echo "error: missing skill directory: $skill_dir" >&2
  exit 1
fi

mkdir -p "${output_path:h}"
rm -f "$output_path"

(
  cd "$skill_dir"
  files=("${(@f)$(find . -type f \( -name '*.md' -o -name '*.json' -o -name '*.py' \) | sort)}")

  if (( ${#files[@]} == 0 )); then
    echo "error: no release files found under $skill_dir" >&2
    exit 1
  fi

  zip -r "$output_path" "${files[@]}"
)

echo "created $output_path"
