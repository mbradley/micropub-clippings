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
CONTENT_DIR=/path/to/your/content/clippings
EOF
```

`CONTENT_DIR` is required - this is where draft files are created. Use an absolute path.

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

# Collect last 3 days into today's post (catch up after missing days)
./clippings --last 3

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
- **Catch-up mode**: Use `--last N` to collect multiple days into one post
- **Link notes**: Notes on bookmarks appear as italicized text
- **Highlights**: Highlights are included as blockquotes
- **Update support**: First publish saves URL; subsequent publishes update the existing post
- **Timezone handling**: UTC timestamps converted to local time
- **Slug**: Sends `{category}-YYYY-MM-DD` via `mp-slug` (note: [Micro.blog ignores mp-slug](https://help.micro.blog/t/supporting-mp-slug-summary-and-type-on-the-micropub-endpoint/2072))
- **Configurable**: Collection, tag, category, publish time, and output directory customizable via environment
- **Optional categories**: Category in frontmatter and Micropub is optional—omit for no category

## Configuration

Required in `.env`:

```
RAINDROP_API_TOKEN=...                      # Raindrop API token
MICROBLOG_TOKEN=...                         # Micro.blog app token
CONTENT_DIR=/path/to/content/clippings      # Output directory (absolute path)
```

Optional overrides:

```
RAINDROP_COLLECTION=Clippings    # Raindrop collection name (default: Clippings)
RAINDROP_TAG=mchn                # Tag to filter by (default: mchn)
MICROBLOG_CATEGORY=clippings     # Category for posts and slug prefix (omit for none)
PUBLISH_TIME=23:59               # Time for published posts in HH:MM (default: 23:59)
```

If `MICROBLOG_CATEGORY` is set, posts will include a `categories` field in frontmatter and the category will be sent to Micropub. The slug will be `{category}-YYYY-MM-DD`. If omitted, no category is used and the slug is just `YYYY-MM-DD`.

### Editor

After creating or updating a draft, the script opens it in your editor. Set the `EDITOR` environment variable to customize:

```bash
# In your shell profile (~/.zshrc, ~/.bashrc, etc.):
export EDITOR="vim"           # Terminal editor
export EDITOR="code --wait"   # VS Code (waits for file to close)
export EDITOR="subl -w"       # Sublime Text (waits)
export EDITOR="bbedit -w"     # BBEdit on macOS (waits)
export EDITOR="bbedit"        # BBEdit (returns immediately)
```

If `EDITOR` is not set, the script tries these in order: `code`, `subl`, `vim`, `nano`.

Use `--no-edit` to skip opening the editor entirely.

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
