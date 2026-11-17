# Series

Aleksei’s personal television diary, inspired by Letterboxd. A static, responsive website with a poster collection, chronological diary, search, year and status filters, series details, and a monthly activity chart.

**Live:** https://shadrunov.github.io/letterboxd-series/

## Run locally

No dependencies or build step. Use Python 3:

```sh
python3 -m http.server 8000
```

Open http://localhost:8000. Serve the folder over HTTP; opening `index.html` directly cannot fetch the JSON data.

## Update the diary

Edit `data/series.json`. Each entry records a title, the year listed in the original diary, watch month (`YYYY-MM`), seasons, `watched` or `unfinished` status, and a local poster path. To add a series, put its poster in `assets/posters/` and add its entry. Statistics and available years update automatically. Missing months are intentional; watch days are not invented.

The initial nine entries were transcribed from the owner’s Notion diary on 17 November 2026. The empty 2025 heading was omitted. Heartstopper’s listed 2024 year is preserved from the source; it refers to the logged season rather than the series premiere. The source’s “interview with the vampires” title is displayed as “Interview with the Vampire.” Unfinished seasons count as logged seasons.

```sh
python3 scripts/check.py
```

## Publishing

The GitHub Actions workflow validates the data and deploys only the website files to GitHub Pages on pushes to `main`. Repository Settings → Pages should use **GitHub Actions** as its source. No tokens, Notion access, or API calls are required by the published website.

## Credits

This is an independent personal site, unaffiliated with Letterboxd. Posters and show metadata were retrieved from [TVmaze](https://www.tvmaze.com/) and attributed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/); each entry links to its source show and records its source image URL. Artwork belongs to its respective rights holders.
