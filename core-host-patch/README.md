# CORE-HOST changes for RESCS 0.3.1

Based on CORE-HOST-Terminal-Commands-2026-10-20.zip, SHA-256
578c072d90934db389267ccf5aaf996ea092a8ca3f127a18144fae5fb3425ad1.

From the CORE-HOST root:

```text
git apply --check ABSOLUTE_PATH/CORE-HOST-RESCS.patch
git apply ABSOLUTE_PATH/CORE-HOST-RESCS.patch
```

Alternatively back up and replace exactly:
- core/web/storage.py
- core/web/gateway.py

The adapter forwards validated limit/offset and validates page metadata and
saved-record scope. The gateway refuses managed local startup while a different
RESCS endpoint is selected. Existing portal markup shows the first page;
additional pages are available through GET /api/records?limit=N&offset=N.
services.py needs no change: it already supplies the required factory command
and five RESCS configuration variables. CORE-CLIENT needs no source change.
No file-upload or record-ID CRUD portal interface is added.

Back up CORE web configuration and both source files first. Reverse with
`git apply --check -R ABSOLUTE_PATH/CORE-HOST-RESCS.patch`, then
`git apply -R ABSOLUTE_PATH/CORE-HOST-RESCS.patch`, or restore the originals.
No GitHub write or public deployment was performed.
