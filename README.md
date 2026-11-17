# Series

[Aleksei’s series diary](https://shadrunov.github.io/letterboxd-series/) — a static, personal viewing history inspired by Letterboxd.

## Browse

- **Diary:** every viewing, including rewatches and unfinished entries, grouped by year. Choose **Large cards** (five per desktop row), **Small cards** (eight), or **List**. The list has month/year calendars, titles, release years, seasons, rewatch markers, and GitHub edit links. It has no day, rating, or review column.
- **Watched:** one card per series with a completed viewing, across all years. Rewatches are combined, watched seasons and tags are collected, and the latest watch month is shown. Choose large or small cards. Unfinished-only series remain in the diary.

Open a poster or title for its synopsis, complete viewing history, TMDB page, and a verified Letterboxd page when available. Below the details, a seasons list shows release years, episode counts, optional synopses, and links to individual seasons; specials appear last. Unknown dates and episode counts are marked explicitly. Search, tags, year, watch type, layout, and section are shareable in the URL.

## Edit the diary

Open [2026](diary/2026.md) or [2025](diary/2025.md). GitHub displays each file as a readable table. Click the pencil to edit, add a row, and commit to `main`. **Edit year** and each diary entry’s pencil also lead to the corresponding file on GitHub.

Each year is a separate Markdown file in [`diary/`](diary/). Copy its table into `2024.md`, for example, to add that year. New files appear automatically, newest year first. No JSON editing is needed.

| Month | Series | Seasons | Watch | Status | Tags | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Jan | Young Royals | 1-3 | watch | watched | queer, in darmstadt | |
| Sep | Young Royals | 2, 3 | rewatch | watched | w/ friends | |
| Nov | Young Royals | all | rewatch | watched | queer | The whole series again. |

These are examples only, not actual viewing records.

- **Month:** `Jan`, `January`, or `1`. Use `?` or leave blank if you only remember the year.
- **Series:** a registered title or a TMDB link. For a new series, paste its TMDB URL here; the title, release year, synopsis, genres, and poster are retrieved automatically.
- **Seasons:** `1`, `1, 3`, `1-3`, or `all` for the complete series as watched at that time. Leave blank for movie links.
- **Watch:** `watch` or `rewatch`.
- **Status:** `watched` or `unfinished`.
- **Tags:** comma-separated personal tags; spaces, slashes, accents, and emoji work.
- **Notes:** optional personal notes, displayed in details. Use `\|` for a literal pipe.

### TMDB links

For example:

```text
| Jun | https://www.themoviedb.org/tv/124834 | 3 | watch | watched | queer | |
```

Links with slugs, trailing slashes, or Markdown labels such as `[Heartstopper](https://www.themoviedb.org/tv/124834)` also work. Movie URLs use the movie endpoint and are displayed as films; they are never silently converted into TV series.

One row is one viewing. Repeat the same title or link for a rewatch, in the same month, year, or a different year. Specific-season and complete-series rewatches are independent. `all` is never expanded based on later releases.

### Registered titles and Letterboxd

[`data/shows.csv`](data/shows.csv) is a readable table of title aliases and source links:

| Series | TMDB | IMDb | Letterboxd |
| --- | --- | --- | --- |
| Heartstopper | https://www.themoviedb.org/tv/124834 | tt10638036 | |

A registered title can be used directly in a diary row. The CSV contains links only; **all show metadata and posters come from TMDB**. The original nine entries have been matched to TMDB. Their viewing dates and seasons are preserved; release years now follow TMDB (Heartstopper premiered in 2022).

The importer attempts to find Letterboxd pages, checks that their TMDB identifier matches the exact show or film, and caches verified links. A matching title alone is insufficient. Unavailable or blocked pages do not prevent publication and do not produce guessed links. You can also enter a verified canonical `https://letterboxd.com/film/.../` URL in the **Letterboxd** column. The links table applies to both title aliases and direct TMDB URLs.

### Tags

Use free-form tags like [my Letterboxd tags](https://letterboxd.com/shadrunov/tags/): themes (`queer`), languages (`deutsch`), places (`in darmstadt`), and companions (`w/ …`). Tags belong to a viewing, so rewatches can have different tags.

The site discovers tags automatically. Select several to match all of them on a viewing. Search also matches tags and notes. No tags were guessed for the original Notion entries.

## Import and publish

The GitHub Pages workflow imports uncached TMDB titles, validates the diary, runs tests, builds the site, and publishes on pushes to `main`. The repository secret **TMDB_READ_ACCESS_TOKEN** is configured. Both API read tokens and v3 API keys are supported. Credentials are used only on the build runner, never published.

Metadata and posters live in GitHub Actions cache and in the deployed site, not in bot commits. Cache expiry requires another import using the repository secret. The published page needs no server or runtime API calls.

To refresh metadata and check Letterboxd links again, open **Actions → Deploy GitHub Pages → Run workflow** and select **Refresh all referenced TMDB metadata and posters**. The optional URL test checks a TMDB link without adding a viewing. **Resolve catalogue titles to TMDB** is a maintenance helper for resolving the registered catalogue and exporting metadata as an artifact.

## Local preview

Python 3, no packages:

```sh
python3 scripts/import_tmdb.py
python3 scripts/build.py
python3 -m http.server 8000 --directory _site
```

The importer asks for your credential with a hidden prompt if uncached links need fetching, or accepts the `TMDB_READ_ACCESS_TOKEN` environment variable. Cache files are in ignored `.cache/tmdb/`; generated website files are in ignored `_site/`. Rebuild after editing tables, then refresh http://localhost:8000.

```sh
python3 scripts/check.py
python3 -m unittest discover -s scripts -p 'test_*.py'
node scripts/test_app.mjs
```

## Credits

An independent personal site, unaffiliated with Letterboxd. Metadata and artwork: [TMDB](https://www.themoviedb.org/). This product uses the TMDB API but is not endorsed or certified by TMDB. The approved TMDB logo comes from its official developer documentation. Artwork belongs to its respective rights holders.
