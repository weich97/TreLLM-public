# Expected Tests

A passing plugin-author answer should propose at least one deterministic pytest
case that:

- imports the plugin class;
- builds a small synthetic snapshot or fixture;
- verifies the protocol output shape;
- avoids live API calls;
- documents security and data assumptions.
