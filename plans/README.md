# NanoChat Desktop Development Plans

This directory contains all planning documents for the NanoChat Desktop Linux application.

---

## Quick Start

1. **Read First**: [`CLAUDE.md`](../CLAUDE.md) - Instructions for LLM assistants
2. **Overview**: [`nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) - High-level architecture
3. **API Reference**: [`other plan docs/api-docs.md`](other%20plan%20docs/api-docs.md) - Backend API documentation
4. **Start Building**: Check [`pending-tasks.md`](pending-tasks.md) - Prioritized task list

---

## Document Index

### Active Task Tracking

| Document | Description |
|----------|-------------|
| [`pending-tasks.md`](pending-tasks.md) | **MASTER TASK LIST** - All pending work, prioritized by criticality |
| [`completed-items.md`](completed-items.md) | **COMPLETED WORK** - Archive of all finished features and releases |

### Core Reference Documents

| Document | Description |
|----------|-------------|
| [`../CLAUDE.md`](../CLAUDE.md) | LLM assistant instructions, coding standards, workflow |
| [`nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) | High-level architecture, tech stack, project structure |
| [`github-workflow.md`](github-workflow.md) | Git workflow, releases, issue tracking |

### Archived Phase Plans

*The original phase-specific plans have been moved to the [`other plan docs/`](other%20plan%20docs/) folder for reference. These documents contain detailed implementation notes that may still be useful, but all task tracking now happens in `pending-tasks.md`.*

| Phase | Version | Document | Status |
|-------|---------|----------|--------|
| 1 | v0.1.0 | [`other plan docs/phase-1-mvp.md`](other%20plan%20docs/phase-1-mvp.md) | ✅ Complete |
| 1 | v0.1.0 | [`other plan docs/phase-1-review.md`](other%20plan%20docs/phase-1-review.md) | ✅ Review |
| 2 | v0.2.0 | [`other plan docs/phase-2-enhanced-ux.md`](other%20plan%20docs/phase-2-enhanced-ux.md) | ✅ Complete |
| 3 | v0.3.0 | [`other plan docs/phase-3-assistants-projects.md`](other%20plan%20docs/phase-3-assistants-projects.md) | Pending |
| 4 | v0.4.0 | [`other plan docs/phase-4-advanced-features.md`](other%20plan%20docs/phase-4-advanced-features.md) | Pending |
| 5 | v1.0.0 | [`other plan docs/phase-5-polish.md`](other%20plan%20docs/phase-5-polish.md) | Pending |

### Additional Reference Documents

| Document | Description |
|----------|-------------|
| [`other plan docs/api-docs.md`](other%20plan%20docs/api-docs.md) | Complete NanoChat backend API documentation |
| [`other plan docs/future-enhancements.md`](other%20plan%20docs/future-enhancements.md) | Post-v1.0 feature ideas (integrated into pending-tasks.md) |

---

## Project Summary

**Repository**: `nanochat-desktop-v2`
**Tech Stack**: Python 3.11+, GTK4/Libadwaita, httpx, Pydantic, SQLite
**Packaging**: Flatpak, AppImage

### Current Status

**Version**: v0.2.0 (Released)
**Next Phase**: v0.3.0 - Assistants and Projects

### Version Timeline

```
v0.1.0  →  v0.2.0  →  v0.3.0  →  v0.4.0  →  v1.0.0
  ↓          ↓          ↓          ↓          ↓
  ✅         ✅          🔄         ⏳         ⏳
 MVP     Enhanced    Assistants  Advanced   Polish
 Chat       UX       Projects    Features   Release
```

Legend: ✅ Complete | 🔄 In Progress | ⏳ Pending

---

## Task Tracking Workflow

**IMPORTANT**: The project now uses a consolidated task tracking system. Do NOT create new phase-specific plans.

### For Development Sessions:

1. **Pick a task** from [`pending-tasks.md`](pending-tasks.md)
   - Tasks are organized by priority: CRITICAL → HIGH → MEDIUM → LOWER
   - Start with CRITICAL priority tasks

2. **Implement the feature**
   - Reference archived phase plans in [`other plan docs/`](other%20plan%20docs/) for implementation details
   - Follow coding standards in [`../CLAUDE.md`](../CLAUDE.md)

3. **Mark as complete**
   - Move the task from `pending-tasks.md` to `completed-items.md`
   - Add completion date

4. **Continue** with next task

### Task Statistics

| Priority | Count | Focus |
|----------|-------|-------|
| CRITICAL | 6 | Core UX (copy, shortcuts, rename, search, etc.) |
| HIGH | 15 | Organization (assistants, projects, TTS/STT, export) |
| MEDIUM | 15 | Power User (web search, attachments, analytics) |
| LOWER | 22 | Polish (themes, accessibility, documentation) |
| EXPERIMENTAL | 4 | Future consideration (local LLM, plugins) |
| **TOTAL** | **60** | |

---

## For LLM Assistants

When working on this project:

1. **Always read [`../CLAUDE.md`](../CLAUDE.md) first** - Contains coding standards and guidelines
2. **Check [`pending-tasks.md`](pending-tasks.md)** - Pick the next prioritized task
3. **Reference archived plans** - See [`other plan docs/`](other%20plan%20docs/) for implementation details
4. **Check API docs** - See [`other plan docs/api-docs.md`](other%20plan%20docs/api-docs.md) for endpoint signatures
5. **Follow git workflow** - See [`github-workflow.md`](github-workflow.md)

### Key Reminders

- Use Python 3.11+ with type hints
- GTK4/Libadwaita for UI (not GTK3)
- Async/await for all network operations
- XDG directories for data storage
- libsecret for API key storage
- Conventional commits for git
- **Work from `pending-tasks.md`, not phase plans**

---

## For Human Developers

### Getting Started

1. Review the documentation in order:
   - [`../CLAUDE.md`](../CLAUDE.md) - Coding standards
   - [`nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) - Architecture
   - [`pending-tasks.md`](pending-tasks.md) - Current tasks

2. Set up development environment:
   ```bash
   # See phase-1-mvp.md in "other plan docs/" for full instructions
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Pick a task from `pending-tasks.md` and start building!

### Human Tasks (Per Phase)

Some tasks require human action:

| Phase | Human Tasks |
|-------|-------------|
| 1 | Create repo, set up environment |
| 2 | Gather feedback from Phase 1 |
| 3 | (none) |
| 4 | (none) |
| 5 | Create app icon, screenshots |

### Release Process

1. Complete all phase tasks from `pending-tasks.md`
2. Update version numbers
3. Tag release (matches branch name)
4. Build Flatpak and AppImage
5. Create GitHub release with binaries

See [`github-workflow.md`](github-workflow.md) for detailed instructions.

---

## Questions?

- **Current Tasks**: See `pending-tasks.md`
- **Implementation Details**: See archived phase plans in `other plan docs/`
- **API**: See `other plan docs/api-docs.md`
- **Architecture**: See `nanochat-desktop-development-plan.md`
- **Git/Releases**: See `github-workflow.md`
