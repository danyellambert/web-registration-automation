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

---

## 10. HTML Structure Reference

### 10.1 `login.html`

Main elements used by the automation:

- email field: `id="email"`, `name="email"`
- password field: `id="password"`, `name="password"`
- submit button: `id="pgtpy-botao"`

Main user-facing sections:

- title block: `RegFlow Platform`
- subtitle: `Sign in to continue`
- footer with logo and signature text

### 10.2 `products.html`

Main elements used by the automation:

- `product_code`
- `brand`
- `product_type`
- `category`
- `unit_price`
- `cost`
- `notes`
- submit button: `id="pgtpy-botao"`
- clear button: `id="pgtpy-botao-limpar"`

Rendered output sections:

- product registration form
- registered products table
- footer with logo and signature text

### 10.3 `index.html`

Behavior:

- sets `<title>RegFlow Platform</title>`
- redirects immediately to `login.html`

---

## 11. Client-Side Behavior Reference

### 11.1 Login page behavior

`login.html` performs:

- required-field validation on all inputs
- inline error messages using `<small>` elements
- redirect to `products.html` when validation passes

### 11.2 Products page behavior

`products.html` performs:

- required validation on all fields except `notes`
- local table rendering through DOM insertion
- product persistence to `localStorage`
- restore-on-load from `localStorage`
- full clear/reset through the **Clear** button

### 11.3 Storage contract

The page currently stores registered products using:

- `localStorage` key: `productList`

Stored format:

- array of arrays, ordered as:
  1. `product_code`
  2. `brand`
  3. `product_type`
  4. `category`
  5. `unit_price`
  6. `cost`
  7. `notes`

This is important because `registration_web.py` reads this structure as one of the submission evidence sources.

---

## 12. Asset Reference

### 12.1 Shared assets

- `assets/main_logo.webp`: platform logo used for favicon, touch icon, and footer branding

### 12.2 Login page assets

- `login_assets/main_styles.css`
- `login_assets/main_app.js`
- `login_assets/app_chunk_a.js`
- `login_assets/app_chunk_b.js`
- `login_assets/webfont.9f87595f89.js`
- `login_assets/jquery-3.5.1.min.dc5e7f18c8.55a31caff3.js`

### 12.3 Products page assets

- `products_assets/main_styles.css`
- `products_assets/main_app.js`
- `products_assets/app_chunk_a.js`
- `products_assets/app_chunk_b.js`
- `products_assets/webfont.9f87595f89.js`
- `products_assets/jquery-3.5.1.min.dc5e7f18c8.55a31caff3.js`

---

## 13. Selector Stability Notes

The Selenium runtime depends on the stability of the current UI identifiers and structure. In practice, the following should be treated as automation contracts:

- login input IDs/names
- product form field IDs/names
- submit button `id="pgtpy-botao"`
- product table structure under `.pgtpy-container-tabela`
- `localStorage` key `productList`

If any of these change, the automation may still work through fallback selectors, but `registration_web.py` should be reviewed and updated intentionally.

---

## 14. Local Verification Checklist

After changing this front-end, validate at least the following:

1. start the static server

   ```bash
   python -m http.server 8000 --directory web_page/exclusive_page
   ```

2. open `login.html` and confirm:
   - branding appears correctly
   - login validation works
   - redirection to `products.html` works

3. open `products.html` and confirm:
   - all fields are visible
   - a new row appears after submit
   - `Clear` removes stored rows

4. run automation smoke test from project root:

   ```bash
   MAX_RECORDS=5 HEADLESS=0 KEEP_OPEN=1 python registration_web.py
   ```

---

## 15. Relationship with the Rest of the Repository

This front-end is directly connected to the rest of the project in the following ways:

- `registration_web.py` automates it
- `.github/workflows/registration-web.yml` can serve it locally in the GitHub runner
- `.github/workflows/deploy-web-page.yml` publishes it to GitHub Pages
- `README.md` documents it at repository level
- `docs/ARCHITECTURE.md` and `docs/OPERATIONS.md` reference it as the target interface

---

## 16. Known Limitations

- there is no backend persistence; storage is browser-local only
- login is simulated client-side and does not authenticate against a server
- product data is not shared across browsers/devices unless automation captures it into CSV history
- the page is intended as a controlled automation target, not as a production web application backend
