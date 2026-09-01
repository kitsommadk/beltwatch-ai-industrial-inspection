# Fail-closed checks

The store rejects wrong lane identities and mismatched camera/frame/position context before creating a shared observation. The database separately rejects duplicate shared-frame identity, invalid geometry ranges and broken foreign-key references.

These checks prevent a relationship record from silently joining unrelated lane evidence.
