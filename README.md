# Clippings

Publish curated bookmarks from Raindrop.io to Micro.blog.

## Overview

This script fetches bookmarks from a Raindrop.io collection, formats them as markdown with excerpts, notes, and highlights, and publishes them to Micro.blog via Micropub.

## Installation

### Option A: pipx (recommended)

```bash
pipx install git+https://github.com/mbradley/micropub-clippings.git
```

This installs a global `clippings` command.

### Option B: Clone and run directly

```bash
git clone https://github.com/mbradley/micropub-clippings.git
cd micropub-clippings
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Setup

### 1. Configure API tokens

Create a `.env` file with your tokens. The script searches these locations (in order):

1. `./.env` (current directory)
2. `~/.config/micropub-clippings/.env`
3. Script directory (for development)

```bash
# For global config:
mkdir -p ~/.config/micropub-clippings
cat > ~/.config/micropub-clippings/.env << 'EOF'
RAINDROP_API_TOKEN=your_raindrop_token
MICROBLOG_TOKEN=your_microblog_token
EOF
```

**Raindrop token**: https://app.raindrop.io/settings/integrations → Create app → Create test token

**Micro.blog token**: https://micro.blog/account/apps → Generate Token

### 2. Raindrop setup

- Create a collection (default name: "Clippings")
- Tag bookmarks you want to publish (default tag: `#mchn`)

These defaults can be changed via environment variables (see Configuration below).

## Usage

```bash
# Create/update local draft for today
./clippings

# Create draft for a specific date (backfill)
./clippings --date 2026-01-15

# Publish to Micro.blog
./clippings --publish

# Publish a backdated post
./clippings --publish --date 2026-01-15

# Skip opening editor
./clippings --no-edit

# Show help
./clippings --help
```

## Workflow

1. Save bookmarks to Raindrop throughout the day
2. Add them to your configured collection with the configured tag
3. Add notes and highlights in Raindrop as desired
4. Run `./clippings` to generate local draft
5. Preview locally, make any edits
6. Run `./clippings --publish` to publish/update on Micro.blog

Running multiple times pulls fresh data from Raindrop, so notes and highlights are always current.

## Output Format

```markdown
- [Article Title](https://example.com)

    Excerpt from the article.

    *Your note on the link*

    > Highlighted passage from the article
```

## Features

- **Fresh data**: Each run regenerates from current Raindrop data
- **Link notes**: Notes on bookmarks appear as italicized text
- **Highlights**: Highlights are included as blockquotes
- **Update support**: First publish saves URL; subsequent publishes update the existing post
- **Timezone handling**: UTC timestamps converted to local time
- **Predictable URLs**: Posts use `{category}-YYYY-MM-DD` slug
- **Configurable**: Collection, tag, category, and output directory customizable via environment

## Configuration

Add optional settings to your `.env` file to customize behavior:

```
RAINDROP_COLLECTION=Clippings    # Raindrop collection name (default: Clippings)
RAINDROP_TAG=mchn                # Tag to filter by (default: mchn)
MICROBLOG_CATEGORY=clippings     # Category for published posts (default: clippings)
CONTENT_DIR=../content/clippings # Local output directory
```

All settings have sensible defaults and are optional.

## Adapting for Other Services

The script is structured around two main interfaces. To adapt for a different bookmark service or publishing platform, implement these patterns:

### Bookmark Structure

The `fetch_bookmarks()` function returns a list of bookmark dicts:

```python
{
    "title": "Article Title",
    "url": "https://example.com/article",
    "excerpt": "Description or excerpt from the page",  # optional
    "note": "Your note on the bookmark",              # optional
    "highlights": [                                   # optional
        {
            "text": "Highlighted passage",
            "note": "Note on this highlight"          # optional
        }
    ],
    "created": "2026-01-15T10:30:00.000Z"            # ISO 8601 UTC
}
```

To use a different bookmark service (Pinboard, Pocket, etc.), write a new fetcher that returns this structure. Missing fields are handled gracefully.

### Publishing Interface

The `publish_to_microblog()` function expects:

- **Input**: Markdown body content, title, target date, category
- **Output**: Published URL (stored in frontmatter for updates)

It uses [Micropub](https://micropub.spec.indieweb.org/), a W3C standard supported by Micro.blog, WordPress (with plugin), and other IndieWeb platforms.

To use a different publishing platform, replace this function with one that:
1. Creates a new post and returns its URL
2. Updates an existing post given its URL

### Local Draft Structure

Drafts are markdown files with YAML frontmatter:

```markdown
---
title: "Clippings for January 15, 2026"
date: 2026-01-15
type: clippings
micropub_url: https://example.com/published/url  # added after first publish
---

- [Article Title](https://example.com)

    Excerpt text.

    *Your note*

    > Highlighted passage
```

The `micropub_url` field enables update-in-place rather than creating duplicates.

## License

MIT
