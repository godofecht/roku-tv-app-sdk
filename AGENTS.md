# Agent contract

Use `python3 -m roku_ai init SPEC.json` to create a valid sample specification, edit the JSON, then run `python3 -m roku_ai build SPEC.json --out OUTPUT_DIR` and `python3 -m roku_ai package OUTPUT_DIR --out APP.zip`.

Always run `python3 -m unittest discover -s tests -v` before proposing changes.

Generated files are outputs: change the spec or generator instead of hand-editing the build directory.

Never claim a package has passed Roku certification or on-device validation without testing on actual hardware. Do not put credentials in specifications, logs, or committed files. Never deploy to an untrusted device.
