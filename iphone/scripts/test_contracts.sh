#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
output="$(mktemp -d)"
trap 'rm -rf "$output"' EXIT
xcrun --sdk macosx swiftc -module-cache-path "$output/cache" "$root/BeanFitRuntime/RuntimeContracts.swift" \
  "$root/BeanFitRuntime/ModelCatalog.generated.swift" "$root/BeanFitRuntime/ModelSuggestions.swift" "$root/BeanFitRuntime/Models.swift" "$root/JumpingBeansDemo/Shopping.swift" "$root/JumpingBeansDemo/CatalogShopping.swift" \
  "$root/BeanFitRuntime/TextDraft.swift" "$root/Tests/Contracts.swift" -o "$output/contracts"
"$output/contracts"
