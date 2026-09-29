# Keyword Research Publisher

Automates daily keyword research collection and publishes generated HTML reports through GitHub Actions and GitHub Pages.

## Included Automation

- `block1`: trend research reports.
- `block3`: newly registered domain reports.
- `block4`: community signal digests.
- `common`: shared `Item` and `FetchResult` models.

## Local Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp block1/config.example.json block1/config.json
cp block3/config.example.json block3/config.json
cp block4/config.example.json block4/config.json
```

`block4/config.json` may contain Product Hunt or YouTube credentials for local runs. Keep it uncommitted.

## Tests

```bash
python -m unittest test_renderers.py
python -m unittest block3.test_new_domains
```

## Generate Reports Locally

```bash
python -m block1.main --out _generated/trends
python -m block3.main --out _generated/new_domains
python -m block4.main --out _generated/digests
```

## Publish With GitHub Pages

The workflow at `.github/workflows/pages.yml` runs the collectors, stages `_site/`, and deploys the static HTML reports with GitHub Pages.

Each daily run creates date-stamped report pages, for example `trends/trends-YYYY-MM-DD.html`, `new_domains/new-domains-YYYY-MM-DD.html`, and `digests/digest-YYYY-MM-DD.html`. Historical pages are preserved on the `pages-history` branch, while `index.html` and each section index are regenerated to link to the latest and historical reports.

For Product Hunt and YouTube collection in GitHub Actions, add repository secrets at **Settings -> Secrets and variables -> Actions**:

- `PRODUCTHUNT_TOKEN`: Product Hunt developer token.
- `YOUTUBE_API_KEY`: YouTube Data API v3 key.
- `TYPESAFE_API_KEY`: TypeSafe/JEV API key for Google Trends screening.

If a source's secret is missing, that source is skipped where credentials are required. Without `TYPESAFE_API_KEY`, Google Trends terms remain included and marked unscreened. With the key configured, JEV separates durable research candidates from transient or uncertain topics and displays the decision and confidence.

After pushing this repository to GitHub, enable **Settings -> Pages -> GitHub Actions**.
