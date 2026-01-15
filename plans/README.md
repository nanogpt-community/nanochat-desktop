# NanoChat Desktop Development Plans

This directory contains all planning documents for the NanoChat Desktop Linux application.

---

## Quick Start

1. **Read First**: [`CLAUDE.md`](CLAUDE.md) - Instructions for LLM assistants
2. **Overview**: [`nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) - High-level architecture
3. **API Reference**: [`api-docs.md`](api-docs.md) - Backend API documentation
4. **Start Building**: [`phase-1-mvp.md`](phase-1-mvp.md) - Phase 1 implementation guide

---

## Document Index

### Core Documents

| Document | Description |
|----------|-------------|
| [`CLAUDE.md`](CLAUDE.md) | LLM assistant instructions, coding standards, workflow |
| [`nanochat-desktop-development-plan.md`](nanochat-desktop-development-plan.md) | High-level architecture, tech stack, project structure |
| [`api-docs.md`](api-docs.md) | Complete NanoChat backend API documentation |

### Phase Plans

| Phase | Version | Document | Focus |
|-------|---------|----------|-------|
| 1 | v0.1.0 | [`phase-1-mvp.md`](phase-1-mvp.md) | Core chat, API client, basic UI |
| 2 | v0.2.0 | [`phase-2-enhanced-ux.md`](phase-2-enhanced-ux.md) | Search, shortcuts, themes |
| 3 | v0.3.0 | [`phase-3-assistants-projects.md`](phase-3-assistants-projects.md) | Assistants, projects management |
| 4 | v0.4.0 | [`phase-4-advanced-features.md`](phase-4-advanced-features.md) | Web search, attachments, analytics |
| 5 | v1.0.0 | [`phase-5-polish.md`](phase-5-polish.md) | Themes, accessibility, release |

### Additional Documents

| Document | Description |
|----------|-------------|
| [`future-enhancements.md`](future-enhancements.md) | Post-v1.0 feature roadmap |
| [`github-workflow.md`](github-workflow.md) | Git workflow, releases, issue tracking |

---

## Project Summary

**Repository**: `nanochat-desktop-v2`  
**Tech Stack**: Python 3.11+, GTK4/Libadwaita, httpx, Pydantic, SQLite  
**Packaging**: Flatpak, AppImage

### Version Timeline

```
v0.1.0  →  v0.2.0  →  v0.3.0  →  v0.4.0  →  v1.0.0
  ↓          ↓          ↓          ↓          ↓
 MVP     Enhanced    Assistants  Advanced   Polish
 Chat       UX       Projects    Features   Release
```

### Core Features by Phase

**Phase 1 - MVP (v0.1.0)**
- Backend connection with API key
- Streaming chat messages
- Conversation management
- Model selection
- Local SQLite caching

**Phase 2 - Enhanced UX (v0.2.0)**
- Conversation search
- Keyboard shortcuts
- Dark/light themes
- Copy/paste support
- Stop generation

**Phase 3 - Organization (v0.3.0)**
- Assistants management
- Projects management
- Filter by project
- Move conversations

**Phase 4 - Advanced (v0.4.0)**
- Web search integration
- Image attachments
- Document attachments
- Starred messages
- Balance display

**Phase 5 - Release (v1.0.0)**
- Catppuccin theme
- Tokyo Night theme
- Accessibility
- Documentation
- App store readiness

---

## For LLM Assistants

When working on this project:

1. **Always read [`CLAUDE.md`](CLAUDE.md) first** - Contains coding standards and guidelines
2. **Reference phase plans** - Each phase has detailed implementation tasks
3. **Check [`api-docs.md`](api-docs.md)** - For exact API endpoint signatures
4. **Follow git workflow** - See [`github-workflow.md`](github-workflow.md)

### Key Reminders

- Use Python 3.11+ with type hints
- GTK4/Libadwaita for UI (not GTK3)
- Async/await for all network operations
- XDG directories for data storage
- libsecret for API key storage
- Conventional commits for git

---

## For Human Developers

### Getting Started

1. Review the plans in order:
   - High-level plan
   - Phase 1 MVP
   - API docs

2. Set up development environment:
   ```bash
   # See phase-1-mvp.md for full instructions
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Create repository:
   ```bash
   gh repo create nanochat-desktop-v2 --private
   git checkout -b v0.1.0
   ```

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

1. Complete all phase tasks
2. Update version numbers
3. Tag release (matches branch name)
4. Build Flatpak and AppImage
5. Create GitHub release with binaries

See [`github-workflow.md`](github-workflow.md) for detailed instructions.

---

## Questions?

- **Architecture**: See high-level plan
- **API**: See api-docs.md
- **Implementation**: See phase-specific plans
- **Git/Releases**: See github-workflow.md
