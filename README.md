# Series

[Aleksei’s series diary](https://shadrunov.github.io/letterboxd-series/) — a personal viewing history inspired by Letterboxd.

## Add a viewing

Edit [`diary/2026.yaml`](diary/2026.yaml) and add a list element:

```yaml
- url: https://www.themoviedb.org/tv/124834
  date: 2026-07
  seasons: [3]
  tags: [queer, in darmstadt]
```

Commit to `main`. GitHub Actions fetches the TMDB information, fills in `name`, sorts and formats the YAML, commits those changes back, and publishes the site. Afterwards the same entry reads:

```yaml
- url: https://www.themoviedb.org/tv/124834
  name: "Heartstopper"
  date: 2026-07
  seasons: [3]
  tags: [queer, in darmstadt]
```

The examples are illustrative; they are not extra diary records. **You only need to enter the URL, date, seasons, and tags.** Names are maintained automatically. Comments and viewing details are preserved. The action sorts entries newest first, keeps the existing order for equal dates, and standardizes field order, two-space indentation, and compact season/tag lists. JSON is generated internally; you never need to edit it.

Each year has its own YAML file. Add `diary/2024.yaml` with the same list format to add another year. An empty year uses `[]`. Diary edit links on the site open the corresponding YAML file on GitHub.

### Fields

| Field | Format |
| --- | --- |
| `url` | TMDB `/tv/…` or `/movie/…` URL; required |
| `name` | Added or updated by the action from TMDB |
| `date` | `2026-07`, `2026-07-15`, or just `2026`; must match the file’s year |
| `seasons` | `[1, 2, 3]`, a single number, `"1-3"`, or `all`; omit for movies |
| `tags` | A list such as `[queer, deutsch, "w/ alena ❤️"]`; defaults to `[]` |
| `rewatch` | `true` for a repeat viewing; defaults to `false` |
| `status` | `watched` (default) or `unfinished` |
| `notes` | Optional personal notes |

Full dates are preserved in YAML, while the public diary displays only their month. Unknown months can be recorded as a year alone. YAML duplicate keys, misplaced years, invalid dates, unknown fields, and invalid season ranges fail validation before anything is published.

One list element is one viewing. To rewatch selected seasons, add another element with the same URL and `rewatch: true`. This works in the same year, month, or a different year:

```yaml
- url: https://www.themoviedb.org/tv/125910
  date: 2026-10
  seasons: [2, 3]
  tags: [queer]
  rewatch: true
```

Use `seasons: all` for a complete-series rewatch. Use `status: unfinished` if you did not finish it. A green eye marks completed season viewings, with a total counter when watched more than once. Unfinished entries do not count. Complete-series entries count regular seasons released by the logged month/year, without inferring future seasons, specials, or seasons with unknown release dates.

### Different tags for different seasons

Use separate YAML records for the same TMDB URL. For example:

```yaml
- url: https://www.themoviedb.org/tv/125910
  date: 2024-06
  seasons: [1]
  tags: ["w/ alena ❤️"]

- url: https://www.themoviedb.org/tv/125910
  date: 2025-07
  seasons: [2]
  tags: [in dublin]

- url: https://www.themoviedb.org/tv/125910
  date: 2026-02
  seasons: [3]
  tags: [queer]
```

Place each record in its corresponding year file. These are examples, not actual viewing records. A record listing several seasons gives its tags to all those seasons; split it into separate records when their tags differ.

**Diary combines regular-watch records of the same series into one entry**, across years. It shows the union of seasons and tags, dated by the latest `date` field (full dates are used for ordering even though only the month is displayed). The example above appears once in February 2026 with S1, S2, S3 and all three tags. Entering an older date later does not move the merged entry forward.

Records with `rewatch: true` remain separate dated entries. Source YAML is never merged or rewritten by this display feature. Profile ENTRIES/THIS YEAR counters still count source records. The green-eye season counters also use source records, so grouping does not create extra watches. A merged entry is marked unfinished if any source record is still unfinished; update that record when you finish it.

Diary filters run **after** grouping: tags from different seasons can match together, and the year filter uses the merged entry’s latest date. A year whose records all moved into a later merged entry does not display a misleading empty-year section. The merged row’s pencil opens the latest record; its details show all original records, tags, notes, and their own GitHub edit links. Individual seasons also display their corresponding tags.

## Browse

- **Diary:** merged regular watches plus separate rewatches, grouped by their displayed year. Large cards (five per desktop row), small cards (eight), or a list with year-only calendars and a separate month column. The list has no day, rating, or review column.
- **Watched:** one card per series with a completed viewing, across all years. Rewatches are combined. Choose large or small cards.

Search is at the top right. Filters sit directly above the entries. Search, tags, year, watch type, layout, and section are shareable in the URL. Select multiple tags to match all of them on a viewing. Search also matches notes.

Open a title or poster for its synopsis, viewing history, season release years and episode counts, TMDB links, and verified Letterboxd links when available. All metadata and posters come from TMDB. [`data/shows.csv`](data/shows.csv) contains optional verified Letterboxd links; new YAML entries do not need catalogue rows.

## Publishing

Pushes to `main` refresh all referenced TMDB records, enrich names, sort and format diary files, lint YAML, run tests, build, commit changed YAML, and deploy through GitHub Pages. The repository’s configured **TMDB_READ_ACCESS_TOKEN** secret accepts a read token or v3 API key. Credentials are used only on the build runner.

Only diary YAML changes are committed by the bot, after successful checks. The workflow uses the standard `GITHUB_TOKEN` and a `[skip ci]` commit to avoid recursion. A normal push protects concurrent edits: it never force-pushes or overwrites a newer user commit.

Metadata and posters use Actions cache; the published page embeds its diary data and versions script/style URLs by content. The static site needs no server or runtime API calls. Metadata refreshes on every deployment and daily at 05:17 UTC. You can also run **Actions → Deploy GitHub Pages → Run workflow**. The site remains static between deployments; counts follow the latest TMDB data.

When TMDB catalogues a renamed season as a separate series, [`data/season-continuations.yaml`](data/season-continuations.yaml) records a verified continuation and season offset. Its seasons are fetched from TMDB and shown under the original series with their own TMDB links. This includes *The Vampire Lestat* as season 3 of *Interview with the Vampire*. Your diary still records only the seasons you watched. If TMDB later reunites the records, native seasons take precedence to avoid duplicates.

## Local preview

Python 3:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/import_tmdb.py --write-names
python3 scripts/format_diary.py
python3 scripts/build.py
python3 -m http.server 8000 --directory _site
```

The importer asks for a credential with a hidden prompt if uncached links need fetching, or accepts the `TMDB_READ_ACCESS_TOKEN` environment variable. Rebuild after editing YAML, then refresh http://localhost:8000. `.cache/` and `_site/` are ignored by Git.

```sh
python3 scripts/format_diary.py --check
python3 -m yamllint --strict -c .yamllint.yaml diary data/season-continuations.yaml .github/workflows/pages.yml .yamllint.yaml
python3 scripts/check.py
python3 -m unittest discover -s scripts -p 'test_*.py'
node scripts/test_app.mjs
```

## Credits

An independent personal site, unaffiliated with Letterboxd. Metadata and artwork: [TMDB](https://www.themoviedb.org/). This product uses the TMDB API but is not endorsed or certified by TMDB. The approved TMDB logo comes from its official developer documentation. Artwork belongs to its respective rights holders.

Typography uses self-hosted [Inter](https://github.com/rsms/inter) and [Source Serif 4](https://github.com/adobe-fonts/source-serif), under the SIL Open Font License. License files are included in `assets/fonts/`.
