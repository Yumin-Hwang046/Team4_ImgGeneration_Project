Put mood preset images in this folder with these exact file names:

- `warm.png`
- `clean.png`
- `trendy.png`
- `premium.png`
- `default.png`

`call_image_generator()` maps selected mood to one of these files.
If a mood file is missing, `default.png` is used.
If `default.png` is also missing, the pipeline falls back to the uploaded user image as the reference.
