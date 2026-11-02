# Userdata backup gate — updated 3 November 2026

No verified p10 host-evidence bundle has been provided or found in the reviewed
local artifact directories. StageB and StageC remain blocked.

Use the complete [Image96 read-only host procedure](persistent-storage-96.md).
It replaces this page's old example, which incorrectly included `conv=noerror`
and verified only the backup file's own hash. Neither is acceptable evidence
of a complete source copy.

Required: exact30334779392-byte raw p10 image from a stable/unmounted source,
full read without I/O errors, host filesystem/encryption/feature inspection,
independent complete O_DIRECT source read, matching source/image SHA256,
retained raw evidence and a reviewed BigPart-aware offline restore procedure.
Do not save it on the tablet, exported USB device or in GitHub.

The new readiness command uses --host-inspection and verifies the underlying
bundle rather than trusting a JSON `inspection_passed` boolean. It does not
flash, repair, mount RW, authorize writes or restore anything. Dirty/encrypted/
unknown filesystems remain blocked for writable mounting even if backed up.
