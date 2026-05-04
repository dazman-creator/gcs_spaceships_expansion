# GURPS Spaceships (GCS Master Library Expansion)

This repository contains a full implementation of the GURPS Spaceships 1 rules for GCS (GURPS Character Sheet).

## Version

Current target GCS version is stored in `VERSION`.

This project tracks the current GCS version directly. When GCS updates, update `VERSION`, refresh the library files for the new GCS release, run the tests below, then push to `master`. The JSON `"version": 5` inside the files is the GCS file schema version, not the app release number.

## Features
- Automated Ship Mass scaling via Lifting ST.
- Armor DR location mapping (Front, Center, Rear).
- Propulsions translating Gs to Basic Move.
- Generic Weapon Batteries pre-calculated by SM.
- Power Point token system.

## Tests

Run before pushing updates:

```powershell
python tests/validate_library.py
python test_generator.py --count 50
```

GitHub Actions runs the same checks on every push or pull request to `master`.
