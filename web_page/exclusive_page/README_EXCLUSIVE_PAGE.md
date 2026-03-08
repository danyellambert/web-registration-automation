# RegFlow Platform — Exclusive Page Front-end

This directory contains the static front-end used as the Selenium automation target (`registration_web.py`) and as the content published to GitHub Pages.

---

## Table of Contents

- [1. Purpose](#1-purpose)
- [2. File Structure](#2-file-structure)
- [3. Page Flow](#3-page-flow)
- [4. Current Branding](#4-current-branding)
- [5. Run Locally](#5-run-locally)
- [6. Publish with GitHub Pages](#6-publish-with-github-pages)
- [7. Integration with Automation](#7-integration-with-automation)
- [8. Maintenance Guidelines](#8-maintenance-guidelines)
- [9. Quick Troubleshooting](#9-quick-troubleshooting)

---

## 1. Purpose

This front-end provides a simple web app for:

1. login (`login.html`)
2. product registration (`products.html`)
3. local persistence through browser `localStorage`

It supports both local testing and cloud automation execution (`target_site=local_runner` or `target_site=github_pages` in GitHub Actions).

---

## 2. File Structure

```text
web_page/exclusive_page/
├── .nojekyll
├── README_EXCLUSIVE_PAGE.md
├── index.html
├── login.html
├── products.html
├── assets/
│   └── main_logo.webp
├── login_assets/
│   ├── app_chunk_a.js
│   ├── app_chunk_b.js
│   ├── main_app.js
│   ├── main_styles.css
│   ├── jquery-3.5.1.min.dc5e7f18c8.55a31caff3.js
│   ├── ns.3b4f746746.html
│   └── webfont.9f87595f89.js
└── products_assets/
    ├── app_chunk_a.js
    ├── app_chunk_b.js
    ├── main_app.js
    ├── main_styles.css
    ├── jquery-3.5.1.min.dc5e7f18c8.55a31caff3.js
    ├── ns.3b4f746746.html
    └── webfont.9f87595f89.js
```

---

## 3. Page Flow

### 3.1 `index.html`

- entry point
- automatically redirects to `login.html`

### 3.2 `login.html`

- login form with `email` and `password`
- client-side required field validation
- redirects to `products.html` after successful submit

### 3.3 `products.html`

- product registration form with:
  - `product_code`
  - `brand`
  - `product_type`
  - `category`
  - `unit_price`
  - `cost`
  - `notes`
- renders the registered products table
- persists records in `localStorage` under `productList`

---

## 4. Current Branding

Platform name:

- **RegFlow Platform**

Footer elements:

- logo: `assets/main_logo.webp`
- signature text: **Danyel Lambert**

Branding appears in:

- `index.html` (`<title>`)
- `login.html` (main title + logo `alt` + footer)
- `products.html` (logo `alt` + footer)

---

## 5. Run Locally

From the project root, run:

```bash
python -m http.server 8000 --directory web_page/exclusive_page
```

Useful URLs:

- Home: http://127.0.0.1:8000/
- Login: http://127.0.0.1:8000/login.html
- Products: http://127.0.0.1:8000/products.html

If visual updates do not appear immediately, perform a hard refresh (`Cmd + Shift + R` on macOS/Chrome).

---

## 6. Publish with GitHub Pages

Workflow:

- `.github/workflows/deploy-web-page.yml`

Automatic deployment is triggered on pushes to `main` when these paths change:

- `web_page/exclusive_page/**`
- `.github/workflows/deploy-web-page.yml`

### One-time repository configuration

1. Open **Settings → Pages**
2. Under **Build and deployment**, select **Source: GitHub Actions**

Public URL:

- https://danyellambert.github.io/web-registration-automation/

---

## 7. Integration with Automation

`registration_web.py` uses this folder in two ways:

1. **Default local target**
   - `LOGIN_URL=http://127.0.0.1:8000/login.html`
2. **Local auto-start resilience**
   - if `AUTO_START_LOCAL_SITE=1` and local URL is offline, the runtime attempts:

```bash
python -m http.server <port> --bind <host> --directory web_page/exclusive_page
```

The automation selectors are aligned with this UI's `id`/`name` fields and button structure.

---

## 8. Maintenance Guidelines

When editing the front-end, preserve (or update in Python at the same time):

- login and products form field IDs/names
- submit button behavior in `products.html`
- `localStorage` key (`productList`) or equivalent logic

Typical front-end changes that require updates in `registration_web.py`:

- field `id`/`name` renames
- submit button structure/text changes
- product table DOM structure changes

---

## 9. Quick Troubleshooting

### 9.1 Local page does not open

- ensure the HTTP server is running on port 8000
- verify with:

```bash
curl -I http://127.0.0.1:8000/login.html
```

### 9.2 Visual updates do not appear

- hard refresh (`Cmd + Shift + R`)
- test in a private/incognito tab

### 9.3 GitHub Pages did not update

- check workflow status: **Deploy web_page to GitHub Pages**
- confirm your commit changed files under `web_page/exclusive_page/**`
