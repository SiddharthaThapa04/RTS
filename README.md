# 🍅 Rotten Tomatoes Movie Scraper

A Robocorp automation robot that scrapes movie metadata and critic reviews from Rotten Tomatoes, persists results to a local SQLite database, and delivers a formatted HTML report via email.

---

## Overview

Given a list of movie titles in an Excel workbook, this robot:

1. Searches Rotten Tomatoes for each title
2. Applies exact-match logic to resolve the correct result (preferring the most recent release when duplicates exist)
3. Scrapes scores, metadata, storyline, and up to six critic reviews per movie
4. Persists all results to a local SQLite database (`movies.db`)
5. Emails the complete dataset as an HTML table report

Movies that cannot be matched or scraped are stored with `NDF` (No Data Found) placeholder values so the output remains structurally consistent across all runs.

---

## Prerequisites

| Requirement                                | Version |
| ------------------------------------------ | ------- |
| Python                                     | 3.10+   |
| Robocorp / `rcc` CLI                       | Latest  |
| A Gmail account with App Passwords enabled | —       |

> **Note:** This robot uses `robocorp-browser` (Playwright under the hood). The browser binary is managed automatically by `rcc` — no manual Playwright installation is required.

---

## Project Structure

```
.
├── tasks.py          # Main robot entry point
├── movies.xlsx       # Input workbook (see Input Format below)
├── robot.yaml        # Robocorp task definition
├── conda.yaml        # Environment & dependency spec
└── movies.db         # SQLite output (created on first run)
```

---

## Input Format

The robot reads from `movies.xlsx` in the project root. The workbook must contain a sheet named **`data`** with a single column named **`Movies`**:

| Movies         |
| -------------- |
| The Godfather  |
| Dune: Part Two |
| Oppenheimer    |

One movie title per row. Titles are matched case-insensitively against Rotten Tomatoes search results.

---

## Configuration

Before running, open `tasks.py` and update the three email constants near the top of the file:

```python
SENDER_EMAIL    = "your-gmail-address@gmail.com"
SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password — NOT your login password
RECEIVER_EMAIL  = "recipient@example.com"
```

### Generating a Gmail App Password

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already active
3. Navigate to **Security → App Passwords**
4. Generate a new App Password for _Mail / Other_
5. Paste the 16-character password into `SENDER_PASSWORD`

> Standard Gmail login passwords will not work. App Passwords are required for SMTP access.

---

## Running the Robot

### With `rcc` (recommended)

```bash
rcc run
```

`rcc` creates an isolated environment from `conda.yaml`, installs all dependencies, and executes the task defined in `robot.yaml`.

### With an existing Python environment

```bash
pip install robocorp robocorp-browser RPA.Excel.Files
python -m robocorp.tasks run tasks.py -t rts
```

---

## Output

### Database

Results are written to `movies.db` in the working directory. Each run performs `INSERT OR REPLACE`, so re-running the robot with the same titles will overwrite existing records with fresh data.

**Schema — `movies` table:**

| Column                  | Type      | Description               |
| ----------------------- | --------- | ------------------------- |
| `title`                 | TEXT (PK) | Movie title (from input)  |
| `year`                  | INTEGER   | Release year              |
| `tomatometer`           | TEXT      | Critic score              |
| `audience_score`        | TEXT      | Audience score            |
| `storyline`             | TEXT      | Synopsis                  |
| `genre`                 | TEXT      | Genre(s), comma-separated |
| `runtime`               | TEXT      | Runtime                   |
| `rating`                | TEXT      | MPAA rating               |
| `release_date`          | TEXT      | Theatrical release date   |
| `critic_1` … `critic_6` | TEXT      | Critic review summaries   |

Critic fields follow the format:

```
Name (Publication) [SENTIMENT]: review text
```

Where `SENTIMENT` is one of `POSITIVE`, `NEGATIVE`, or `UNKNOWN`.

### Email Report

Once all movies are processed, a single email is sent to `RECEIVER_EMAIL` containing the full `movies` table rendered as an HTML table. Subject line: **RT Movie Scrape Results**.

---

## Behaviour & Matching Logic

- Only **exact** title matches (case-insensitive) are accepted. Partial matches are ignored.
- When multiple exact matches exist for the same title, the **most recently released** version is selected.
- If a title produces no results, or no exact match can be found, an `NDF` record is written to the database and the robot continues with the next title.
- Any row-level failure is caught and logged; the robot resets browser state and continues rather than aborting the entire run.

---

## Troubleshooting

**`[ERROR] Search page did not load`**
Rotten Tomatoes may be rate-limiting requests. Increase the `slowmo` value in `tasks.py`:

```python
browser.configure(slowmo=300)  # milliseconds between actions
```

**`[WARN] Could not click Movies filter`**
The Movies tab UI occasionally fails to render in time. The robot proceeds without the filter and will still attempt an exact-match lookup — results are usually unaffected.

**`SMTPAuthenticationError`**
Verify that the value in `SENDER_PASSWORD` is a Gmail App Password, not your regular account password. See the [Configuration](#configuration) section above.

**`NDF` results for titles that exist on RT**
Check for special characters or subtitle formatting differences between the input title and the Rotten Tomatoes listing (e.g. colons, ampersands). Adjust the input to match the site's canonical title.

---

## License

Licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

You may use, reproduce, and distribute this work in compliance with the License.
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an **"AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND**, either express or implied.
