# PDF Library Manager (PDF-LM)

Self-hosted server for organizing, indexing, and browsing PDF game manuals and guides. Think Jellyfin/Plex, but for PDFs—with intelligent OCR, metadata enrichment, duplicate detection, and multi-user access.

## Features

✅ **Intelligent OCR Pipeline**
- Conditional multi-pass OCR (Tesseract + PaddleOCR)
- Detects embedded text; only OCRs when needed
- Embeds text back into PDFs for full-text searchability

✅ **Metadata Enrichment**
- Automatic extraction of title, author, ISBN, dates
- Lookup via Google Books & Open Library APIs
- User confirmation for uncertain matches
- Manual override in web UI

✅ **Smart File Organization**
- User-configurable naming templates
- Support for local, NAS, and cloud storage
- Automatic organization by publisher/game/title

✅ **Multi-User Access**
- Role-based permissions (Admin, Curator, Viewer)
- Personal collections/shelves
- Reading status tracking

✅ **Web UI & REST API**
- Jellyfin/Plex-like aesthetic
- Full-text search
- Admin panel
- REST API for integrations

## Quick Start

```bash
# Clone & enter directory
git clone https://github.com/jbowensii/PDFLibraryManager.git
cd PDFLibraryManager

# Start dev environment
docker-compose -f docker-compose.dev.yml up

# Access:
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## Documentation

- **Design Spec:** [docs/specs/2026-06-28-pdf-library-manager-design.md](docs/specs/2026-06-28-pdf-library-manager-design.md)
- **Architecture:** [docs/architecture/](docs/architecture/)
- **API Reference:** http://localhost:8000/docs (when running)

## Development

Open in VS Code:
```bash
code PDFLibraryManager.code-workspace
```

Run tests:
```bash
docker-compose -f docker-compose.dev.yml exec backend pytest tests/ -v
docker-compose -f docker-compose.dev.yml exec frontend npm test
```

## License

MIT License

## Status

🚧 **Under Development** — MVP implementation in progress. Design specification complete and approved.
