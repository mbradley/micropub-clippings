#!/usr/bin/env python3
"""
Fetch bookmarks from Raindrop.io and create/update clippings posts.

Usage:
    ./scripts/clippings              # Today's clippings (creates local draft)
    ./scripts/clippings --date 2026-01-15  # Specific date (backfill)
    ./scripts/clippings --publish    # Publish today's clippings to Micro.blog
    ./scripts/clippings --publish --date 2026-01-15  # Publish backdated
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' package required. Install with: pip install python-dotenv")
    sys.exit(1)

# Configuration
RAINDROP_API_BASE = "https://api.raindrop.io/rest/v1"
MICROPUB_ENDPOINT = "https://micro.blog/micropub"
COLLECTION_NAME = "Clippings"
TAG_FILTER = "mchn"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "clippings"


def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: {env_path} not found.")
        print("Copy .env.example to .env and fill in your tokens.")
        sys.exit(1)
    load_dotenv(env_path)


def get_raindrop_token():
    """Get Raindrop API token."""
    token = os.getenv("RAINDROP_API_TOKEN")
    if not token:
        print("Error: RAINDROP_API_TOKEN not set in .env file")
        sys.exit(1)
    return token


def get_microblog_token():
    """Get Micro.blog API token."""
    token = os.getenv("MICROBLOG_TOKEN")
    if not token:
        print("Error: MICROBLOG_TOKEN not set in .env file")
        print("Get one at: https://micro.blog/account/apps")
        sys.exit(1)
    return token


def raindrop_request(endpoint, token, params=None):
    """Make authenticated request to Raindrop API."""
    headers = {"Authorization": f"Bearer {token}"}
    url = urljoin(RAINDROP_API_BASE + "/", endpoint.lstrip("/"))
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_collection_id(token, collection_name):
    """Find collection ID by name."""
    data = raindrop_request("/collections", token)
    for collection in data.get("items", []):
        if collection.get("title", "").lower() == collection_name.lower():
            return collection["_id"]

    # Also check root collections
    data = raindrop_request("/collections/childrens", token)
    for collection in data.get("items", []):
        if collection.get("title", "").lower() == collection_name.lower():
            return collection["_id"]

    print(f"Error: Collection '{collection_name}' not found")
    print("Available collections:")
    data = raindrop_request("/collections", token)
    for c in data.get("items", []):
        print(f"  - {c.get('title')}")
    sys.exit(1)


def fetch_bookmarks(token, collection_id, target_date):
    """Fetch bookmarks from collection with tag filter for a specific date."""
    # Raindrop search with tag filter
    # Date filtering is done client-side since API search is limited
    params = {
        "search": f"#{TAG_FILTER}",
        "perpage": 50,
        "page": 0,
    }

    data = raindrop_request(f"/raindrops/{collection_id}", token, params)
    bookmarks = []

    target_date_str = target_date.strftime("%Y-%m-%d")

    for item in data.get("items", []):
        # Parse the created date - Raindrop returns UTC timestamps
        created = item.get("created", "")
        if created:
            # Raindrop returns ISO format: 2026-01-17T10:30:00.000Z
            # Convert UTC to local time for date comparison
            try:
                utc_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                local_dt = utc_dt.astimezone()  # Convert to local timezone
                item_date = local_dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                # Fallback to simple string extraction if parsing fails
                item_date = created[:10]

            if item_date == target_date_str:
                bookmarks.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("link", ""),
                    "excerpt": item.get("excerpt", ""),
                    "note": item.get("note", ""),
                    "highlights": item.get("highlights", []),
                    "created": created,
                })

    return bookmarks


def parse_existing_post(filepath):
    """Parse existing clippings post, return (frontmatter_dict, links, body_content).

    Links is a dict mapping URL -> full markdown line(s) for that link.
    """
    if not filepath.exists():
        return None, {}, None

    content = filepath.read_text()

    # Split frontmatter and body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_str = parts[1].strip()
            body = parts[2].strip()
        else:
            frontmatter_str = ""
            body = content
    else:
        frontmatter_str = ""
        body = content

    # Parse frontmatter into dict
    frontmatter = {}
    for line in frontmatter_str.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"')

    # Parse links from body - look for markdown links in list items
    links = {}
    # Match list items that contain links
    # This regex captures the full list item including any following indented excerpt
    link_pattern = re.compile(r'^\s*-\s+\[([^\]]+)\]\(([^)]+)\)(.*?)(?=^\s*-\s+\[|\Z)',
                              re.MULTILINE | re.DOTALL)

    for match in link_pattern.finditer(body):
        url = match.group(2)
        full_match = match.group(0).rstrip()
        links[url] = full_match

    return frontmatter, links, body


def format_bookmark(bookmark):
    """Format a single bookmark as markdown."""
    title = bookmark["title"]
    url = bookmark["url"]
    excerpt = bookmark.get("excerpt", "").strip()
    note = bookmark.get("note", "").strip()
    highlights = bookmark.get("highlights", [])

    # Build the list item
    line = f'- [{title}]({url})'

    # Add excerpt as indented paragraph if present
    if excerpt:
        # Clean up excerpt - remove excessive whitespace
        excerpt = " ".join(excerpt.split())
        line += f'\n\n    {excerpt}'

    # Add user's note on the link if present
    if note:
        note = " ".join(note.split())
        line += f'\n\n    *{note}*'

    # Add highlights as blockquotes if present
    if highlights:
        for hl in highlights:
            hl_text = hl.get("text", "").strip()
            if hl_text:
                # Clean up and format as blockquote
                hl_text = " ".join(hl_text.split())
                line += f'\n\n    > {hl_text}'
                # Add highlight note if present
                hl_note = hl.get("note", "").strip()
                if hl_note:
                    line += f'\n    >\n    > — *{hl_note}*'

    return line


def generate_frontmatter(target_date, micropub_url=None):
    """Generate YAML frontmatter for a clippings post."""
    date_str = target_date.strftime("%Y-%m-%d")
    title_date = target_date.strftime("%B %-d, %Y")

    fm = f"""---
title: "Clippings for {title_date}"
date: {date_str}
type: clippings"""
    if micropub_url:
        fm += f"\nmicropub_url: {micropub_url}"
    fm += "\n---"
    return fm


def save_micropub_url(filepath, url):
    """Save the published Micropub URL to the post's frontmatter."""
    content = filepath.read_text()

    if "micropub_url:" in content:
        # Update existing URL
        content = re.sub(r'micropub_url:.*', f'micropub_url: {url}', content)
    else:
        # Add URL to frontmatter (before closing ---)
        content = content.replace("\n---\n", f"\nmicropub_url: {url}\n---\n", 1)

    filepath.write_text(content)


def create_or_update_post(target_date, bookmarks):
    """Create or regenerate a clippings post with fresh data from Raindrop."""
    # Ensure content directory exists
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    date_str = target_date.strftime("%Y-%m-%d")
    filepath = CONTENT_DIR / f"{date_str}.md"

    if not bookmarks:
        print(f"No bookmarks found for {date_str} matching criteria.")
        print(f"  Collection: {COLLECTION_NAME}")
        print(f"  Tag: #{TAG_FILTER}")
        return None

    # Preserve micropub_url if it exists
    micropub_url = None
    if filepath.exists():
        frontmatter, existing_links, _ = parse_existing_post(filepath)
        micropub_url = frontmatter.get("micropub_url")
        print(f"Regenerating post with {len(bookmarks)} link(s) (was {len(existing_links)})")
    else:
        print(f"Creating new clippings post with {len(bookmarks)} link(s)")

    # Always regenerate from fresh Raindrop data
    content = generate_frontmatter(target_date, micropub_url)
    content += "\n"
    for bookmark in bookmarks:
        content += "\n" + format_bookmark(bookmark)

    filepath.write_text(content + "\n")
    return filepath


def get_post_filepath(target_date):
    """Get the filepath for a clippings post."""
    date_str = target_date.strftime("%Y-%m-%d")
    return CONTENT_DIR / f"{date_str}.md"


def publish_to_microblog(filepath, target_date):
    """Publish or update a clippings post to Micro.blog via Micropub."""
    if not filepath.exists():
        print(f"Error: No local draft found at {filepath}")
        print("Run without --publish first to create a draft.")
        sys.exit(1)

    token = get_microblog_token()

    # Parse the post
    frontmatter, links, body = parse_existing_post(filepath)

    if not body or not body.strip():
        print("Error: Post has no content to publish.")
        sys.exit(1)

    title = frontmatter.get("title", f"Clippings for {target_date.strftime('%B %-d, %Y')}")
    existing_url = frontmatter.get("micropub_url")

    # Prepare Micropub request
    headers = {
        "Authorization": f"Bearer {token}",
    }

    if existing_url:
        # Update existing post
        print(f"Updating existing post on Micro.blog...")
        print(f"  URL: {existing_url}")
        print(f"  Links: {len(links)}")

        # Micropub update uses JSON format
        headers["Content-Type"] = "application/json"
        import json
        data = json.dumps({
            "action": "update",
            "url": existing_url,
            "replace": {
                "content": [body],
                "name": [title],
            }
        })

        response = requests.post(MICROPUB_ENDPOINT, headers=headers, data=data)

        if response.status_code in (200, 204):
            print(f"\nUpdated successfully!")
            return True
        else:
            print(f"\nError updating: {response.status_code}")
            print(response.text)
            return False
    else:
        # Create new post
        print(f"Publishing new post to Micro.blog...")
        print(f"  Title: {title}")
        print(f"  Date: {target_date.strftime('%Y-%m-%d')}")
        print(f"  Links: {len(links)}")

        # Use form-encoded data for Micropub create
        slug = f"clippings-{target_date.strftime('%Y-%m-%d')}"
        data = {
            "h": "entry",
            "name": title,
            "content": body,
            "published": target_date.strftime("%Y-%m-%dT12:00:00"),
            "category": "clippings",
            "mp-slug": slug,
        }

        response = requests.post(MICROPUB_ENDPOINT, headers=headers, data=data)

        if response.status_code in (201, 202):
            location = response.headers.get("Location", "")
            print(f"\nPublished successfully!")
            if location:
                print(f"  URL: {location}")
                # Save the URL to frontmatter for future updates
                save_micropub_url(filepath, location)
                print(f"  Saved URL to frontmatter for future updates")

            return True
        else:
            print(f"\nError publishing: {response.status_code}")
            print(response.text)
            return False


def open_in_editor(filepath):
    """Open file in user's preferred editor."""
    editor = os.environ.get("EDITOR", "")

    if not editor:
        # Try common editors
        for ed in ["code", "subl", "vim", "nano"]:
            if subprocess.run(["which", ed], capture_output=True).returncode == 0:
                editor = ed
                break

    if editor:
        subprocess.run([editor, str(filepath)])
    else:
        print(f"Created: {filepath}")
        print("Set $EDITOR to open automatically")


def main():
    parser = argparse.ArgumentParser(
        description="Create/update clippings posts from Raindrop.io",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./scripts/clippings                    # Create local draft for today
  ./scripts/clippings --date 2026-01-15  # Create draft for specific date
  ./scripts/clippings --publish          # Publish today's draft to Micro.blog
  ./scripts/clippings --publish -d 2026-01-15  # Publish backdated
        """
    )
    parser.add_argument(
        "--date", "-d",
        type=str,
        help="Date for clippings (YYYY-MM-DD format, default: today)"
    )
    parser.add_argument(
        "--no-edit",
        action="store_true",
        help="Don't open editor after creating/updating"
    )
    parser.add_argument(
        "--publish", "-p",
        action="store_true",
        help="Publish to Micro.blog (requires existing local draft)"
    )
    args = parser.parse_args()

    # Load environment
    load_env()

    # Parse target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = datetime.now()

    # Publish mode
    if args.publish:
        filepath = get_post_filepath(target_date)
        publish_to_microblog(filepath, target_date)
        return

    # Draft mode - fetch from Raindrop and create/update local file
    print(f"Fetching clippings for {target_date.strftime('%Y-%m-%d')}...")

    # Get Raindrop token
    token = get_raindrop_token()

    # Find collection
    collection_id = get_collection_id(token, COLLECTION_NAME)

    # Fetch bookmarks
    bookmarks = fetch_bookmarks(token, collection_id, target_date)

    # Create or update post
    filepath = create_or_update_post(target_date, bookmarks)

    if filepath and not args.no_edit:
        open_in_editor(filepath)

    if filepath:
        print(f"\nDraft ready at: {filepath}")
        print(f"Preview locally, then publish with: ./scripts/clippings --publish" +
              (f" --date {args.date}" if args.date else ""))


if __name__ == "__main__":
    main()
