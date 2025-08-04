# utils/

This folder contains utility modules for CornucopiaV2.

## Contents
- **io_helpers.py**: Functions for saving, reading, and writing protocol files.
- **fixed_header.py**: Provides the standard Opentrons protocol header for all generated code.
- **validate.py**: Input validation and missing parameter checks.

## Usage in Pipeline
Utilities are imported by agents and the main app to:
- Format protocol files
- Validate user input
- Add required headers to generated code
- Handle file I/O for protocol simulation
