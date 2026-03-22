"""Release name parser — extracts metadata from torrent/usenet release names.

Based on patterns used by Radarr/Sonarr for identifying media type, quality, and title.
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedRelease:
    title: str
    year: int | None = None
    is_tv: bool = False
    is_movie: bool = False
    season: int | None = None
    episode: int | None = None
    quality: str | None = None
    codec: str | None = None
    source: str | None = None
    release_group: str | None = None


# TV patterns: S01E02, S01, 1x02, Season 1, etc.
TV_PATTERNS = [
    r"[.\s_-]S(\d{1,2})E(\d{1,3})",        # S01E02
    r"[.\s_-]S(\d{1,2})[.\s_-]?E(\d{1,3})", # S01.E02
    r"[.\s_-](\d{1,2})x(\d{1,3})",          # 1x02
    r"[.\s_-]S(\d{1,2})[.\s_-]",            # S01 (season only)
    r"[.\s_-]Season[.\s_-]?(\d{1,2})",      # Season 1
    r"[.\s_-]S(\d{1,2})(?:$|[.\s_-])",      # S01 at end
]

# Quality patterns
QUALITY_PATTERNS = {
    "2160p": r"2160p|4K|UHD",
    "1080p": r"1080p|1080i|FHD",
    "720p": r"720p|HD",
    "480p": r"480p|SD",
}

# Codec patterns
CODEC_PATTERNS = {
    "x265": r"[xh]\.?265|HEVC",
    "x264": r"[xh]\.?264|AVC",
    "AV1": r"AV1",
    "VP9": r"VP9",
}

# Source patterns
SOURCE_PATTERNS = {
    "BluRay": r"Blu-?Ray|BDRip|BRRip|BDREMUX",
    "WEB-DL": r"WEB-?DL|WEBDL",
    "WEBRip": r"WEBRip|WEB-?Rip",
    "HDTV": r"HDTV",
    "DVDRip": r"DVDRip|DVD-?Rip",
    "CAM": r"CAM|HDCAM|HDTS|TELESYNC",
}


def parse_release_name(name: str) -> ParsedRelease:
    """Parse a release name and extract metadata."""
    result = ParsedRelease(title="")

    clean = name.replace(".", " ").replace("_", " ")

    # Check for TV patterns first
    for pattern in TV_PATTERNS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            result.is_tv = True
            groups = match.groups()
            result.season = int(groups[0]) if groups else None
            if len(groups) > 1:
                result.episode = int(groups[1])
            break

    if not result.is_tv:
        result.is_movie = True

    # Extract quality
    for quality, pattern in QUALITY_PATTERNS.items():
        if re.search(pattern, name, re.IGNORECASE):
            result.quality = quality
            break

    # Extract codec
    for codec, pattern in CODEC_PATTERNS.items():
        if re.search(pattern, name, re.IGNORECASE):
            result.codec = codec
            break

    # Extract source
    for source, pattern in SOURCE_PATTERNS.items():
        if re.search(pattern, name, re.IGNORECASE):
            result.source = source
            break

    # Extract year
    year_match = re.search(r"[.\s_(-](\d{4})[.\s_)-]", name)
    if year_match:
        year = int(year_match.group(1))
        if 1920 <= year <= 2030:
            result.year = year

    # Extract title (everything before the first technical marker)
    title_end_patterns = [
        r"[.\s_-]S\d",          # Season marker
        r"[.\s_-]\d{1,2}x\d",   # 1x02
        r"[.\s_-]\d{4}[.\s_-]", # Year
        r"[.\s_-](?:2160|1080|720|480)p",
        r"[.\s_-](?:WEB|BluRay|HDTV|DVDRip|BDRip)",
        r"[.\s_-](?:[xh]\.?26[45]|HEVC|AVC)",
    ]

    title_text = clean
    earliest_pos = len(title_text)
    for pattern in title_end_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match and match.start() < earliest_pos:
            earliest_pos = match.start()

    title_text = name[:earliest_pos].replace(".", " ").replace("_", " ").strip()
    # Remove trailing dashes/spaces
    title_text = re.sub(r"[\s-]+$", "", title_text)
    result.title = title_text

    # Extract release group (usually after the last dash)
    group_match = re.search(r"-(\w+)(?:\[[\w.]+\])?$", name)
    if group_match:
        result.release_group = group_match.group(1)

    return result


def detect_category(release_name: str) -> str:
    """Detect if a release is a movie or TV show. Returns 'movies' or 'tv'."""
    parsed = parse_release_name(release_name)
    return "tv" if parsed.is_tv else "movies"
