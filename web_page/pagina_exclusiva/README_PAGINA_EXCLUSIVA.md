# Página exclusiva (front-end local)

Esta pasta contém uma página adaptada para uso exclusivo deste projeto.

## Executar localmente

```bash
python -m http.server 8000
```

Abra: http://localhost:8000/login.html

## Deploy no GitHub Pages

Este projeto já possui workflow em `.github/workflows/deploy-web-page.yml`.

### Como publicar

1. No GitHub do repositório, abra **Settings → Pages**.
2. Em **Build and deployment**, selecione **Source: GitHub Actions**.
3. Faça commit/push no branch `main`.
4. Aguarde o workflow **Deploy web_page to GitHub Pages** finalizar.

### URL pública

- Página inicial (redireciona para login):
  `https://danyellambert.github.io/web-registration-automation/`
- Login direto:
  `https://danyellambert.github.io/web-registration-automation/login.html`

Sempre que houver alteração em `web_page/pagina_exclusiva/**`, um novo deploy será feito automaticamente.
