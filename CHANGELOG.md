# Changelog

This file includes a history of past releases. Changes that were not yet added to a release are in the [changelog.d/](./changelog.d) folder.

<!--
⚠️ DO NOT ADD YOUR CHANGES TO THIS FILE! (unless you want to modify existing changelog entries in this file)
Changelog entries are managed by scriv. After you have made some changes to this plugin, create a changelog entry with:
    scriv create
Edit and commit the newly-created file in changelog.d.
If you need to create a new release, create a separate commit just for that. It is important to respect these
instructions, because git commits are used to generate release notes:
  - Modify the version number in `__about__.py`.
  - Collect changelog entries with `scriv collect`
  - The title of the commit should be the same as the new version: "vX.Y.Z".
-->

<!-- scriv-insert-here -->

<a id='changelog-1.0.3'></a>
## v1.0.3 (2024-11-04)

[Bugfix] Only show navigation template in popup window if enabled
[Improvement] Set margin to a fixed 25px so viewport doesn't constantly change when resizing

<a id='changelog-1.0.2'></a>
## v1.0.2 (2024-10-31)

[Improvement] Return error to studio if parsing imsmanifest fails. (by @geoff-va)

<a id='changelog-1.0.1'></a>
## v1.0.1 (2024-09-16)

- [Security] Adds authenticated/enrollment check at assets_proxy endpoint

<a id='changelog-1.0.0'></a>
## v1.0.0 (2024-09-12)

- **NOTE**: Beginning fork of [overhangio/openedx-scorm-xblock](https://github.com/overhangio/openedx-scorm-xblock/tree/v18.0.2)
- [Feature] Allows author to specify an existing s3 path to serve scorm files from instead of uploading the package each time (by @geoff-va)
- [Feature] Adds `ScormState` and `ScormInteraction` models to track some basic analytics for aggregation and reporting (by @geoff-va)
  - `ScormInteraction` is not currently enabled but the implementation is there
- [Bugfix] Removes `renderjson.js` from studio authorview as it was causing unit navigation to randomly fail
  - This script is used to pretty-print scorm user state for admin's
  - The user search endpoint returns a 403 if `runtime.user_is_staff` is `False`, but that property does not appear to exist in the studio runtime environment (Olive) so would never work anyway

<a id='changelog-18.0.2'></a>
## v18.0.2 (2024-07-01)

- [Bugfix] Scorm file upload error which zip is compressed with Windows OS. (by @talhaaslam01)

- [Bugfix] Fix a bug where the scorm block would fail to load with an error message `No module named 'importlib_resources'` (by @kdmccormick)

<a id='changelog-18.0.1'></a>
## v18.0.2 (2024-06-21)

- [Bugfix] Make addition of block usage key in scorm path backward compatible. (by @ziafazal)

<a id='changelog-18.0.0'></a>
## v18.0.0 (2024-05-29)

- [Improvement] Add a scriv-compliant changelog. (by @Danyal-Faheem)

- [Bugfix] Prevent overwriting of exported course scorm data by imported course. (by @Danyal-Faheem)
  - Use usage_key instead of block_id as the location identifier for scorm data as it is unique across course imports.
  - This change will not take effect for previously created scorm modules.

- [Improvement] Removed student information and other scorm data from get value func and sends it as part of
`scorm_data` in student view. (By @ahmed-arb)
 - Added `cmi.score.scaled` to uncached_values,
 - Removed old test cases.
