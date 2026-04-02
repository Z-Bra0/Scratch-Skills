#!/bin/zsh

set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
skill_parent_dir="${repo_root}/skills"
skill_name="scratch-blocks"

if (( $# != 1 )); then
  echo "usage: $0 <version>" >&2
  echo "example: $0 v0.0.2" >&2
  exit 1
fi

version="$1"

if [[ ! "$version" =~ '^v[0-9]+(\.[0-9]+)*$' ]]; then
  echo "error: version must look like v0.0.2" >&2
  exit 1
fi

output_path="${repo_root}/dist/${skill_name}-${version}.zip"

if ! command -v zip >/dev/null 2>&1; then
  echo "error: zip is required but was not found in PATH" >&2
  exit 1
fi

if [[ ! -d "${skill_parent_dir}/${skill_name}" ]]; then
  echo "error: missing skill directory: ${skill_parent_dir}/${skill_name}" >&2
  exit 1
fi

mkdir -p "${output_path:h}"
rm -f "$output_path"

(
  cd "$repo_root"
  files=("${(@f)$(find "skills/${skill_name}" -type f \( -name '*.md' -o -name '*.json' -o -name '*.py' \) | sort)}")

  if (( ${#files[@]} == 0 )); then
    echo "error: no release files found under skills/${skill_name}" >&2
    exit 1
  fi

  zip -r "$output_path" "${files[@]}"
)

echo "created $output_path"
