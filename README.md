# The Cape Pool Journal

Pool care, building and fun, written for Cape Town, by Cape Town Pool Maintenance.

- Write and schedule posts at `/admin`
- Posts live in `content/` and images in `assets/img/`
- Netlify runs `python3 build.py` and publishes `public/`
- `netlify/functions/daily-publish.mts` rebuilds the site every morning at 06:05 so scheduled posts go live
