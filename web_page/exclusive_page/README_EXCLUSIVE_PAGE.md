# Exclusive page (local front-end)

This folder contains the page adapted for this project.

## Run locally

```bash
python -m http.server 8000
```

Open: http://localhost:8000/login.html

## Deploy to GitHub Pages

This project already includes the workflow in `.github/workflows/deploy-web-page.yml`.

### How to publish

1. In the repository, open **Settings → Pages**.
2. In **Build and deployment**, select **Source: GitHub Actions**.
3. Commit/push to the `main` branch.
4. Wait for **Deploy web_page to GitHub Pages** to finish.

### Public URL

- Home page (redirects to login):
  `https://danyellambert.github.io/web-registration-automation/`
- Direct login:
  `https://danyellambert.github.io/web-registration-automation/login.html`

Any change in `web_page/exclusive_page/**` triggers an automatic deploy.
