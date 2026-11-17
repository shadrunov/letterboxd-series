# Series

[Aleksei’s series diary](https://shadrunov.github.io/letterboxd-series/) — a personal viewing history inspired by Letterboxd, with compact cards and a list, grouped by year, newest year first.

## Edit the diary

**Open [2026](diary/2026.md) or [2025](diary/2025.md).** GitHub displays each file as a readable table. Click the pencil to edit, add a row, and commit to `main`. The site updates automatically. The website also has an **Edit year** link for each section.

Each year has its own Markdown file in [`diary/`](diary/). Copy a year’s table to `2024.md`, for example, to add that year; it will appear automatically in the right order. No JSON editing is needed.

| Month | Series | Seasons | Watch | Status | Tags | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Jan | Young Royals | 1-3 | watch | watched | queer, in darmstadt | |
| Sep | Young Royals | 2, 3 | rewatch | watched | w/ friends | |
| Nov | Young Royals | all | rewatch | watched | queer | The whole series again. |

**These are examples only, not actual viewing records.**

- **Month:** `Jan`, `January`, or `1`. Use `?` or leave blank if you only remember the year.
- **Series:** a TMDB link (recommended), or a plain series title. Reuse the same link or title for later viewings.
- **Seasons:** `1`, `1, 3`, `1-3`, or `all` for the complete series as you watched it at that time.
- **Watch:** `watch` for a regular entry, `rewatch` for a repeat viewing.
- **Status:** `watched` or `unfinished`.
- **Tags:** any comma-separated labels. Leave blank if none.
- **Notes:** optional personal notes. Use `\|` if your text contains a pipe character.

### Rewatches

One row is one viewing, not one unique series. Add a new row for each rewatch, whether it happens in the same year, month, or a different year. Specific seasons and complete-series rewatches are supported independently. An unfinished rewatch is supported too. Open a series on the site to see its other viewing entries.

Unique-series statistics count the title once; viewing and rewatch statistics count rows. Nothing guesses whether a repeat row was a rewatch: mark it explicitly. `all` means all seasons at the time of that viewing and is never expanded based on later releases.

### Tags

Tags follow the free-form style of [my Letterboxd tags](https://letterboxd.com/shadrunov/tags/): themes (`queer`), languages (`deutsch`), places (`in darmstadt`), and viewing companions (`w/ …`). Tags belong to a particular viewing, so a rewatch can have different tags.

Enter tags in the **Tags** column, separated by commas. Spaces, slashes, accents, and emoji are supported. The site discovers them automatically and offers clickable filters in both views. Select several tags to show entries with **all** of them. Search also matches tags and notes. No personal tags were guessed or assigned to the original Notion entries.

### Add a show with a TMDB link

Put the show’s TMDB link directly in the **Series** cell. GitHub Actions retrieves the title, release year, genres, summary, and poster when you commit. You only fill in your viewing details.

```text
| Jun | https://www.themoviedb.org/tv/100088 | 3 | watch | watched | queer | |
```

This is an editing example, not an actual diary record. Links with a title slug or trailing slash also work. A Markdown link such as `[Heartstopper](https://www.themoviedb.org/tv/100088)` works too. The canonical TMDB title is used for display.

For a complete rewatch, use `all` and `rewatch`. For selected seasons, use `1, 3` or `1-3`. Repeating a link creates another viewing; metadata and posters are fetched only once per title.

`/movie/` links work too, including the supplied `https://www.themoviedb.org/movie/1751639/`. Leave **Seasons** blank for a movie. It is imported through TMDB’s movie endpoint and displayed as a film; movie links are never silently converted into TV entries. The supplied link has not been added as a viewing or fetched without credentials.

#### One-time TMDB setup

1. Get your **API Read Access Token** from [TMDB account → API](https://www.themoviedb.org/settings/api). Use the long read access token, not the shorter v3 API key.
2. Open [this repository’s Actions secrets](https://github.com/shadrunov/letterboxd-series/settings/secrets/actions) and add **TMDB_READ_ACCESS_TOKEN** as a repository secret. Never put it in a file or diary row.
3. Add a TMDB link to a year table and commit. The existing Pages workflow handles import, validation, build, and deployment automatically.

Credentials stay in Actions, and the published site makes no TMDB API requests. Generated metadata and downloaded posters are kept in GitHub Actions cache and included in the published site, not committed back to your repository. A cache miss or expiry requires the secret to fetch the data again. This avoids bot commits and extra deployment loops.

To refresh cached titles and posters, open **Actions → Deploy GitHub Pages → Run workflow**, check **Refresh all referenced TMDB metadata and posters**, and run it.

#### Import locally

```sh
python3 scripts/import_tmdb.py
python3 scripts/build.py
```

The importer asks for your read token with a hidden prompt if uncached links need fetching. It also accepts the `TMDB_READ_ACCESS_TOKEN` environment variable for automation. Files are saved under the ignored `.cache/tmdb/` directory. Use `python3 scripts/import_tmdb.py --refresh` to update cached metadata.

The import fails clearly for an invalid link, missing token, missing title, or failed API request; it does not publish placeholder information for a TMDB entry. Existing plain-title entries and previously imported cached titles do not need credentials to build.

### Plain titles and manual posters

Just add a new title to a year table: it works immediately with a placeholder poster. Optionally add its metadata to [`data/shows.csv`](data/shows.csv), which GitHub also displays as a table, and put a poster in `assets/posters/`. The CSV uses the series title to match diary rows, ignoring capitalization. Year, poster, TVmaze URL, genres, summary, and image source live here once per show, rather than being repeated in every viewing.

The nine original entries came from the owner’s Notion diary. The empty 2025 section is retained without inventing viewings. Heartstopper’s listed 2024 year is preserved from the source; the source’s “interview with the vampires” title is displayed as “Interview with the Vampire.”

## Local preview

Python 3 only, no dependencies:

```sh
python3 scripts/import_tmdb.py
python3 scripts/build.py
python3 -m http.server 8000 --directory _site
```

Open http://localhost:8000. After editing a table, run the build again and refresh. `_site/` is generated and ignored by Git. JSON is an internal build output; yearly Markdown tables are the source of truth.

```sh
python3 scripts/check.py
python3 -m unittest discover -s scripts -p 'test_*.py'
```

## Publishing

Pushes to `main` import uncached TMDB links, validate the tables, build the static site, and deploy it through GitHub Actions to GitHub Pages. The published site needs no runtime server, tokens, Notion access, or API calls. TMDB imports use the repository secret during the build. Search, view, year, status, watch type, and selected tags are shareable in the page URL.

## Credits

An independent personal site, unaffiliated with Letterboxd. Posters and metadata: [TVmaze](https://www.tvmaze.com/), attributed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/); each catalogue row records the original show and image URLs. Artwork belongs to its respective rights holders.

TMDB metadata uses the [official API](https://developer.themoviedb.org/reference/tv-series-details). TMDB’s logo is sourced from its official developer documentation. This product uses the TMDB API but is not endorsed or certified by TMDB.
