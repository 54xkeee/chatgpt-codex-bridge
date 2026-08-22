#!/bin/zsh

set -u

usage() {
  print -u2 -r -- "Usage: verify-tunnel-client.zsh --binary <absolute-path> [--archive <absolute-path> --checksums <absolute-path>]"
}

binary_input=""
archive_input=""
checksums_input=""

while (( $# > 0 )); do
  case "$1" in
    --binary)
      (( $# >= 2 )) || { usage; exit 64; }
      binary_input="$2"
      shift 2
      ;;
    --archive)
      (( $# >= 2 )) || { usage; exit 64; }
      archive_input="$2"
      shift 2
      ;;
    --checksums)
      (( $# >= 2 )) || { usage; exit 64; }
      checksums_input="$2"
      shift 2
      ;;
    *)
      usage
      exit 64
      ;;
  esac
done

if [[ -z "${binary_input}" ]]; then
  usage
  exit 64
fi

if [[ -n "${archive_input}" || -n "${checksums_input}" ]] \
  && [[ -z "${archive_input}" || -z "${checksums_input}" ]]; then
  usage
  exit 64
fi

binary_path="INVALID"
version="UNAVAILABLE"
capability_status="FAIL"
checksum_status="NOT_CHECKED"
archive_status="NOT_CHECKED"
payload_status="NOT_CHECKED"
release_version_status="NOT_CHECKED"
provenance_status="UNVERIFIED"
overall_status="FAIL"

probe_binary_capability() {
  local version_output version_exit version_first_line normalized_version
  [[ "${binary_path}" != "INVALID" && -f "${binary_path}" && -x "${binary_path}" ]] \
    || return 1
  version_output="$("${binary_path}" --version 2>/dev/null)"
  version_exit=$?
  (( version_exit == 0 )) || return 1
  version_first_line="${version_output%%$'\n'*}"
  normalized_version="$(print -r -- "${version_first_line}" | /usr/bin/grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | /usr/bin/head -n 1)"
  if [[ -n "${normalized_version}" ]]; then
    version="${normalized_version}"
    capability_status="PASS"
    return 0
  fi
  version="UNPARSEABLE"
  return 1
}

if [[ "${binary_input}" == /* ]]; then
  binary_path="${binary_input:A}"
fi

if [[ -n "${archive_input}" && -n "${checksums_input}" ]]; then
  provenance_status="FAIL"
  checksum_status="FAIL"
  archive_status="FAIL"
  payload_status="FAIL"
  release_version_status="FAIL"

  if [[ "${archive_input}" == /* && "${checksums_input}" == /* ]]; then
    archive_path="${archive_input:A}"
    checksums_path="${checksums_input:A}"
    archive_base="${archive_path:t}"
    archive_version=""

    if [[ "${archive_base}" == tunnel-client-v*-darwin-arm64.zip ]]; then
      archive_version="${archive_base#tunnel-client-v}"
      archive_version="${archive_version%-darwin-arm64.zip}"
    fi

    if [[ -f "${archive_path}" && -r "${archive_path}" \
       && -f "${checksums_path}" && -r "${checksums_path}" \
       && "${archive_version}" == <->.<->.<-> ]]; then
      expected_digest=""
      while IFS= read -r checksum_line; do
        line_digest="${checksum_line%%[[:space:]]*}"
        line_name="${checksum_line#${line_digest}}"
        line_name="${line_name#"${line_name%%[![:space:]]*}"}"
        line_name="${line_name#\*}"
        if [[ "${line_name}" == "${archive_base}" ]]; then
          expected_digest="${(L)line_digest}"
          break
        fi
      done < "${checksums_path}"

      if [[ "${expected_digest}" =~ '^[0-9a-f]{64}$' ]]; then
        actual_digest_output="$(/usr/bin/shasum -a 256 "${archive_path}" 2>/dev/null)"
        digest_exit=$?
        actual_digest="${(L)actual_digest_output%%[[:space:]]*}"
        if (( digest_exit == 0 )) && [[ "${actual_digest}" == "${expected_digest}" ]]; then
          checksum_status="PASS"
        fi
      fi

      archive_entries_output="$(/usr/bin/unzip -Z1 "${archive_path}" 2>/dev/null)"
      archive_entries_exit=$?
      typeset -a archive_entries
      archive_entries=(${(f)archive_entries_output})
      if (( archive_entries_exit == 0 )) \
        && (( ${#archive_entries[@]} == 1 )) \
        && [[ "${archive_entries[1]}" == "tunnel-client" ]]; then
        archive_status="PASS"
        if [[ "${binary_path}" != "INVALID" && -f "${binary_path}" ]] \
          && /usr/bin/unzip -p "${archive_path}" tunnel-client 2>/dev/null \
             | /usr/bin/cmp -s "${binary_path}" -; then
          payload_status="PASS"
        fi
      fi

    fi
  fi
fi

if [[ -z "${archive_input}" ]]; then
  probe_binary_capability || true
elif [[ "${checksum_status}" == "PASS" \
     && "${archive_status}" == "PASS" \
     && "${payload_status}" == "PASS" ]]; then
  probe_binary_capability || true
  if [[ "${capability_status}" == "PASS" && "${version}" == "${archive_version}" ]]; then
    release_version_status="PASS"
  fi
  if [[ "${release_version_status}" == "PASS" ]]; then
    provenance_status="PASS"
  fi
fi

if [[ "${capability_status}" == "PASS" && "${provenance_status}" == "PASS" ]]; then
  overall_status="PASS"
elif [[ "${capability_status}" == "PASS" && "${provenance_status}" == "UNVERIFIED" ]]; then
  overall_status="UNVERIFIED"
fi

print -r -- "binary_path=${binary_path}"
print -r -- "version=${version}"
print -r -- "capability_status=${capability_status}"
print -r -- "checksum_status=${checksum_status}"
print -r -- "archive_status=${archive_status}"
print -r -- "payload_status=${payload_status}"
print -r -- "release_version_status=${release_version_status}"
print -r -- "provenance_status=${provenance_status}"
print -r -- "overall_status=${overall_status}"

case "${overall_status}" in
  PASS) exit 0 ;;
  UNVERIFIED) exit 2 ;;
  *) exit 1 ;;
esac
