# Clippings

Publish curated bookmarks from Raindrop.io to Micro.blog.

## Overview

This script fetches bookmarks from a Raindrop.io collection, formats them as markdown with excerpts, notes, and highlights, and publishes them to Micro.blog via Micropub.

## Setup

### 1. Install dependencies

```bash
cd scripts
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
```

### 2. Configure API tokens

Copy the example config and add your tokens:

```bash
cp .env.example .env
```

Edit `.env`:

```
RAINDROP_API_TOKEN=your_raindrop_token
MICROBLOG_TOKEN=your_microblog_token
```

**Raindrop token**: https://app.raindrop.io/settings/integrations → Create app → Create test token

**Micro.blog token**: https://micro.blog/account/apps → Generate Token

### 3. Raindrop setup

- Create a collection called "Clippings"
- Tag bookmarks you want to publish with `#mchn`

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
2. Add them to "Clippings" collection with `#mchn` tag
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
- **Predictable URLs**: Posts use `clippings-YYYY-MM-DD` slug

## Configuration

Add optional settings to your `.env` file to customize behavior:

```
RAINDROP_COLLECTION=Clippings    # Raindrop collection name (default: Clippings)
RAINDROP_TAG=mchn                # Tag to filter by (default: mchn)
MICROBLOG_CATEGORY=clippings     # Category for published posts (default: clippings)
CONTENT_DIR=../content/clippings # Local output directory
```

All settings have sensible defaults and are optional.

## License

MIT
