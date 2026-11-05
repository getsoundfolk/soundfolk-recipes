# Soundfolk recipes

Many web radios don't say in their stream which track is playing, but show it on their website.
A **recipe** tells [Soundfolk](https://github.com/getsoundfolk/soundfolk) where to read it: one page,
and where the artist and title are on that page.

This repository is the shared list of recipes. Every copy of Soundfolk downloads it (once a day),
so **a recipe added here gives titles to every listener of that station**.

* Want a station? [Ask for it](https://github.com/getsoundfolk/soundfolk-recipes/issues/new?template=station.yml),
  or click **Ask for a recipe** in Soundfolk (ⓘ in the player) when it finds no title.
* A station shows wrong or no titles? [Report it](https://github.com/getsoundfolk/soundfolk-recipes/issues/new?template=broken.yml), or fix it (below).
* Curious how it works? Read [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Add a station

You need Soundfolk, a text editor and a GitHub account. No git or command line: the app prepares
everything and a bot opens the pull request.

### 1. Check the stream doesn't already announce titles
Play the station in Soundfolk and open its details (ⓘ in the player). If *Track on air* says
"Announced by the stream itself", no recipe is needed.

### 2. Find where the website shows the track on air
* Look for a "now playing", "playlist", "titres diffusés", "on air" or web player page.
* Open your browser's developer tools, *Network* tab, and reload the station's player: the track
  often comes from a **JSON** request (`nowplaying.json`, `/api/live`, `…/current`). Prefer it to
  the HTML page: it changes less often and is smaller to download.
* The page must be **public**: no login, no API key or token in the URL, no cookie needed. If the
  station's own player needs one, the station is not a candidate for now.
* View the page's source (`Ctrl+U`): a recipe reads the HTML sent by the server, not what
  JavaScript adds afterwards. If the track is not in the source, look for the JSON request instead.

### 3. Write the recipe, in the app
The easiest way: in Soundfolk, play the station, open ⓘ and click **Create a recipe**. The app
writes `<id>.toml` in your recipes folder with the station already matched, and opens it in your
editor. Fill in the URL and the selectors, save, come back to Soundfolk: it reloads the file and
the **Test** button shows what it reads.

An HTML page:

```toml
#:schema ../recipe.schema.json
# Fréquence 7 (www.frequence7.net). The stream sends no metadata; the web player shows the
# playlist: li.event_0 is on air, li.event_1 the next track. Times are local.
schema = 1
name = "Fréquence 7"
match = { streams = ["live.aurafm.org/Frequence7"] }
fetch = { url = "https://www.frequence7.net/player/" }

[extract]
type = "html"
item = "li.event_0"           # the element holding the track on air
artist = ".artist"            # CSS selectors, inside the item
title = ".title"
start = ".played-at"          # optional: when the track started
duration = "@data-duration"   # optional: `@attr` = an attribute of the item
next = "li.event_1, li.event_2"
```

A JSON API:

```toml
[extract]
type = "json"
item = "now_playing.song"     # dotted path; `items.0` for the first element of a list
artist = "artist"
title = "title"
start = "played_at"
duration = "duration"
```

The fields at a glance (the full reference is in
[docs/07-now-playing.md](https://github.com/getsoundfolk/soundfolk/blob/main/docs/07-now-playing.md),
and editors that read the `#:schema` line, such as VS Code with *Even Better TOML*, complete and
check them):

| Field | |
|---|---|
| `match.streams` | Stream URLs **without** `http(s)://`: `host/path`. A trailing `*` matches every path that starts with it. |
| `match.stations` | [Radio-Browser](https://www.radio-browser.info/) station UUIDs. Better than streams, which change. Give both when you can. |
| `fetch.url` | The page or JSON to read. Exactly one. |
| `fetch.every` | Optional hint (`"30s"`) when the page has no times. The app has its own limits anyway. |
| `extract.type` | `html` (CSS selectors), `json` (dotted paths) or `text` (one regex with named groups). |
| `item` | Where the track on air is. |
| `artist`, `title` | Inside `item`. Or `text` when the page writes `Artist - Title` in one piece. |
| `start`, `duration` | Optional, but they let the app read the page about once per track instead of every 30 s. Unix time, ISO 8601, or the station's local `HH:MM:SS`; seconds, `MM:SS` or ISO 8601. |
| `next` | Optional: the upcoming tracks, read with the same fields. |
| `cover`, `show` | Optional: cover art URL, name of the show on air. |
| `ignore` | Regexes of titles that aren't tracks: jingles, ads, the station's name. |

### 4. Share it, from the app
When **Test** reads the right track, click **Share this recipe** (you need a GitHub account):

1. Soundfolk reads the page once more and keeps only the part your recipe reads: the **fixture**, a
   small saved copy of the page that lets CI check the recipe without going online. It writes the
   `[[test]]` saying what the recipe must find in it.
2. Your browser opens the *Share a recipe* form here, filled in with the recipe and the fixture
   (when the fixture is too long for a link, it is in your clipboard: paste it into the *Fixture*
   field). Check the **id** (the future file name, it can't change later), tick the licence box and
   submit.
3. A bot checks the recipe and opens a pull request in your name, or comments on the issue with
   what is wrong: edit the issue to try again.

Once a maintainer merges it, every copy of Soundfolk gets the recipe within a day. Soundfolk also
keeps a copy of both files, laid out as in this repository, in `<your recipes folder>/to-share/`.

### Or by hand, with a pull request
1. Put the recipe in `stations/<id>.toml`, with `#:schema ../recipe.schema.json` as its first line.
   The **id** is the file name: lowercase letters, digits, `-` and `_` (`radio-nova`, `fip-jazz`).
   It can't be changed later: choose it after the station.
2. Save the fixture and write the test, with `recipe-check` (needs Rust):

   ```bash
   cargo install --locked --git https://github.com/getsoundfolk/soundfolk soundfolk-nowplaying --bin recipe-check --features cli
   recipe-check fixture stations/<id>.toml   # reads the page now, writes fixtures/<id>.html and the [[test]]
   python3 scripts/lint.py
   recipe-check test stations/<id>.toml
   ```

   Without Rust, save the page (`curl -sS -D headers.txt -o fixtures/<id>.html "<fetch.url>"`), cut it
   down to what the test checks: the track on air, the **next one** and the show, with the elements
   around them that the selectors need; no played tracks, no scripts, styles, trackers or anything
   about users (CI refuses a fixture much larger than that), start it with a comment saying where it comes from (see `fixtures/frequence7.html`), and
   write the test by hand:

   ```toml
   [[test]]
   page = "../fixtures/<id>.html"
   at = "2026-11-04T21:39:08Z"          # when the page was saved: its HTTP Date, in headers.txt
   artist = "BLACK RAINBOWS"
   title = "Children Of Fire And Sacrifices"
   started_at = "2026-11-04T21:36:51Z"  # optional: if the recipe reads `start`
   next_title = "Nino"                  # optional: if it reads `next`
   ```
3. Open a pull request: one station per pull request (a family of stations sharing the same page
   format can come together). CI checks the recipe and replays the fixture.

## Fix a broken recipe
Sites change. When a station shows wrong or no titles:

1. In Soundfolk, open ⓘ on the station and click **Edit locally**: the app copies the recipe in use
   into your recipes folder, where it replaces the shared one on your computer. Fix it until
   **Test** reads the right track.
2. Click **Share this recipe**. The id stays the same, so the pull request updates the recipe in
   place, with a fixture of today's page. (By hand: `recipe-check fixture stations/<id>.toml`, and
   don't rename the file.)

Once your fix is merged and has reached the app, delete your local copy so that you get the next
fixes too.

## What is accepted
* Pages meant for the public: the station's own player, playlist page or the JSON its player uses.
* One URL per recipe, read only while someone listens to the station (the app enforces at least
  15 s between requests, at most 120 per hour, and backs off on errors).
* No credentials, API keys, tokens, or URLs that identify a person.
* No recipe for a station that asks not to be read, or whose terms forbid it. A station owner can
  ask for their recipe to be removed by opening an issue.

## Licence
By contributing, you agree that your recipes are published under the
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/) (the list as a whole) and
the [Database Contents License 1.0](https://opendatacommons.org/licenses/dbcl/1-0/) (each recipe).
Fixtures are excerpts of third-party pages, kept only to test the recipes, and are not covered by
these licences. See [LICENSE](LICENSE).
