# Windows scope

Upstream DeepTutor has a Windows desktop app. This fork's additional local study
layer uses POSIX filesystem locking, shell wrappers and isolated execution.
Use **WSL2 with a Linux distribution** for this layer and follow linux.md.
Native Windows parity is not claimed by upstream desktop support.

Keep the source, Python environment and private study data in the WSL filesystem,
not an accidental mix of Windows and Linux environments. The setup agent must
qualify browser links and any host Anki/Obsidian bridge separately. Ask the human
for the immediate Windows permission/restart action when necessary. One Codex
account and no Modal remain the defaults; do not ask for more services merely
because the host OS differs.
