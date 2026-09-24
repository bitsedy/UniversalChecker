---
scope: templates/**, static/css/**, static/**/*.html
activation: glob
---

# Rules for templates / frontend styling

- Design system is locked: navy (`#14213D`) text on a cream (`#FDFBF5`)
  background, with burnt-orange (`#B8712C`) and teal (`#0F6B5C`) as the two
  accent colors. Playfair Display for headings, Inter for body text. Don't
  introduce a third accent color or a different heading font on a new page
  without flagging it first — consistency across `/`, `/advisor`,
  `/lookup`, and `/guides` matters more than any single page looking
  marginally better in isolation.
- Reuse existing button copy and shape conventions (pill-shaped, bordered,
  colored-text CTAs; phrases like "Retrieve My Voucher," "Read Portal
  Instructions") rather than inventing new phrasing for an action that
  already has an established label elsewhere on the site.
- Card components (result-checker cards, step cards, info boxes) share one
  visual language: white background, ~18–20px radius, a light border, and a
  muted-gray info sub-box for reassurance text. New cards should be built
  from this shared pattern, not styled independently per page.
