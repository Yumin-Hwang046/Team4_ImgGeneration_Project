# Design System Specification: Editorial Softness & Professional Precision

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Human Archive."** 

Moving away from the cold, clinical nature of traditional B2B SaaS, this system adopts a "High-End Editorial" aesthetic. It is inspired by Scandinavian minimalism—where warmth is not an afterthought, but a structural requirement. We achieve a premium feel by prioritizing **asymmetric breathing room**, **tonal layering**, and **typographic authority**.

Instead of a rigid grid of boxes, the UI should feel like a curated gallery. We break the "template" look by using intentional white space as a functional element, overlapping containers to create depth, and utilizing a high-contrast typography scale that prioritizes readability in both Latin and Hangul scripts.

---

## 2. Color & Surface Philosophy
The palette is rooted in organic, earthy tones that establish immediate trust. 

### Core Palette (Material Design Mapping)
- **Primary (`#296678`):** Use for high-emphasis actions and "Authoritative" moments.
- **Primary Container (`#6BA4B8`):** The signature "Dusty Cerulean." Use for secondary actions or soft hero backgrounds.
- **Surface (`#FBF9F6`):** The "Creamy Off-White" base. This is the canvas.
- **On-Surface (`#1B1C1A`):** The "Deep Warm Charcoal." Never use pure black (#000).
- **Secondary Container (`#E9DED2`):** A warm taupe for subtle grouping or muted backgrounds.

### The "No-Line" Rule
**Explicit Instruction:** Prohibit 1px solid borders for sectioning. 
Boundaries must be defined through background color shifts. To separate the sidebar from the main content, do not draw a line; instead, set the sidebar to `surface-container-low` (`#F5F3F0`) against the `surface` (`#FBF9F6`) main area.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the following stack to create natural depth:
1.  **Base Layer:** `surface` (#FBF9F6)
2.  **Sectioning:** `surface-container-low` (#F5F3F0)
3.  **Primary Cards:** `surface-container-lowest` (#FFFFFF) – This provides the "Pure White" pop requested.
4.  **Interaction Layers:** `surface-container-high` (#EAE8E5) – Use for hover states or active tabs.

### The "Glass & Gradient" Rule
To add "soul," use a subtle linear gradient on primary CTAs: from `primary` (#296678) to `primary-container` (#6BA4B8) at a 135-degree angle. For floating overlays (modals/tooltips), use `surface-container-lowest` with an 85% opacity and a `20px` backdrop-blur to create a "Frosted Gallery" effect.

---

## 3. Typography
The typography is designed to be "Quietly Authoritative." We use **Manrope** for its modern, geometric structure in headlines and **Be Vietnam Pro** for its exceptional legibility in body text. Both fonts are chosen for their harmonious pairing with modern Korean typography (Hangul), maintaining consistent stroke weights.

- **Display (Large/Mid/Small):** `manrope` | Bold (700). Use for hero statements and data visualizations.
- **Headline (Large/Mid/Small):** `manrope` | Semi-Bold (600). Use for page titles.
- **Title (Large/Mid/Small):** `beVietnamPro` | Medium (500). Use for card titles and section headers.
- **Body (Large/Mid/Small):** `beVietnamPro` | Regular (400). Optimized for long-form reading.
- **Label (Mid/Small):** `beVietnamPro` | Medium (500) | All-caps with 0.05rem letter spacing. Use for tiny metadata or categories.

*Note: For Korean text, ensure line-height is increased by 10% compared to Latin-only layouts to prevent visual crowding of complex characters.*

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering** rather than structural lines.

- **The Layering Principle:** Place a `surface-container-lowest` (White) card on a `surface-container-low` (Warm Off-white) background. This creates a soft, natural lift.
- **Ambient Shadows:** When an element must "float" (e.g., a dropdown), use a custom shadow: 
  `box-shadow: 0 12px 32px -4px rgba(28, 25, 23, 0.06);` 
  The shadow is tinted with the "Warm Charcoal" color at a very low opacity to mimic natural light.
- **The "Ghost Border" Fallback:** If a border is required for accessibility, use `outline-variant` (#C0C8CC) at **20% opacity**. This creates a suggestion of a boundary without the "boxed-in" feel.

---

## 5. Components

### Buttons
- **Primary:** Gradient (`primary` to `primary-container`), white text, `xl` (1.5rem) rounded corners.
- **Secondary:** `surface-container-highest` background, `on-surface` text. No border.
- **Tertiary:** No background. `primary` text. Underline on hover only.

### Cards & Lists
- **Cards:** Always `surface-container-lowest` (White) with `xl` (1.5rem) corners. Use a `shadow-sm` for a subtle lift.
- **Lists:** **Forbid divider lines.** Use `2.5` (0.85rem) of vertical whitespace to separate items. For active items, use a subtle background shift to `surface-container-low`.

### Input Fields
- **Default:** `surface-container-lowest` background with a `ghost-border` (20% opacity outline-variant). 
- **Focus State:** Increase border opacity to 100% and add a 2px outer "glow" using the `primary-fixed-dim` (#96CFE4) color.

### Chips (Curatorial Tags)
- Use `secondary-container` (#E9DED2) with `on-secondary-container` (#696258) text. Corners should be `full` (9999px) to contrast against the `xl` cards.

### Suggested Component: The "Editorial Breadcrumb"
Instead of standard `Home > Category > Page`, use a large-scale `Label-MD` typography style with generous letter spacing, acting as a "Header Above the Header" to give the UI a magazine-like structure.

---

## 6. Do's and Don'ts

### Do
- **Do** use asymmetric margins. If the left margin is 4 units, try a right margin of 6 units for a bespoke, curated look.
- **Do** use `rounded-xl` for all major containers to maintain the Scandinavian "Softness."
- **Do** prioritize vertical rhythm. Use the Spacing Scale religiously (e.g., always 5.5rem between major sections).

### Don't
- **Don't use emojis.** They undermine the professional, "Curated" authority of the B2B SaaS context.
- **Don't use 100% opaque borders.** They create "visual noise" and break the organic flow of the creamy background.
- **Don't use harsh transitions.** All hover states and transitions should be a minimum of `200ms ease-out` to feel premium and intentional.