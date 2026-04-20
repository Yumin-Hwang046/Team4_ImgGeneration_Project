Put mood-specific preset images in this structure:

- `warm/1.png`, `warm/2.png`, `warm/3.png`, `warm/4.png`
- `clean/1.png`, `clean/2.png`, `clean/3.png`, `clean/4.png`
- `trendy/1.png`, `trendy/2.png`, `trendy/3.png`, `trendy/4.png`
- `premium/1.png`, `premium/2.png`, `premium/3.png`, `premium/4.png`

Optional compatibility files:

- `warm.png`, `clean.png`, `trendy.png`, `premium.png`
- `default.png`

Backend resolves the reference in this order:

1. `{mood}/{selected_preset}` (for example `premium/2.png`)
2. `{mood}/1.png`..`{mood}/4.png`
3. legacy single file (`premium.png`)
4. `default.png`

If all are missing, pipeline falls back to the uploaded user image.
