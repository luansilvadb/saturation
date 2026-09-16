# HTML and CSS Code Style Guide

### HTML semantics — `HTML-SEMANTICS`

- **MUST** use the element that matches the content's meaning; a `<p>` marks a
  paragraph, not spacing.

### Media alternatives — `HTML-MEDIA`

- **MUST** give every `<img>` an `alt` attribute: a description, or `alt=""`
  for an image that is purely decorative.
- **MUST** provide captions or a transcript for audio and video content.

### Separation of concerns — `HTML-SEPARATION`

- **MUST** keep structure in HTML, presentation in CSS, and behavior in
  JavaScript; a stylesheet or a script lives in an external file that the
  document links.
- **MUST NOT** put presentation in a `style` attribute or behavior in an
  inline event handler.

### Document and resources — `HTML-DOCUMENT`

- **MUST** declare `<meta charset="utf-8">` in the head and serve the document
  as UTF-8.
- **MUST** load an embedded resource over HTTPS.

### Selectors — `CSS-SELECTORS`

- **MUST NOT** use an ID selector for styling; style through a class.
- **SHOULD** name a class for the component it describes, not for its
  appearance.

### Cascade — `CSS-CASCADE`

- **MUST NOT** use `!important`; correct the cascade or the selector instead.
