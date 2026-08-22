---
name: TraceVault
description: Replay one AI request with redacted observability, tenant isolation, and operational clarity.
colors:
  background: "#000000"
  surface: "#08101b"
  surface-strong: "#0d1625"
  border-accent: "#00f8f83d"
  border-accent-strong: "#00f8f875"
  text: "#f8f8f8"
  text-muted: "#f8f8f8ad"
  primary: "#0008f8"
  accent: "#00f8f8"
  danger: "#ff667b"
typography:
  display:
    fontFamily: "Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Segoe UI, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
  mono:
    fontFamily: "Consolas, Cascadia Code, Courier New, monospace"
    fontSize: "0.84rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  card: "12px"
  panel: "14px"
  pill: "999px"
spacing:
  sm: "12px"
  md: "18px"
  lg: "32px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#021018"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "48px"
  button-secondary:
    backgroundColor: "#0008f82e"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "48px"
  panel-shell:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "18px"
  badge:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "6px 10px"
---

# Design System: TraceVault

## Overview

**Creative North Star: "The fail-closed operations room"**

TraceVault is an operational product surface for people reconstructing a single AI request under pressure. It should feel like a trusted control plane: dark, precise, and disciplined enough that governance reads as part of the product rather than legal copy pasted nearby.

The interface rejects spectacle. It does not chase dashboard theatrics, generic AI-tool neon, or decorative observability clutter. Every highlight on the screen must point at a user decision: which tenant is active, whether a trace is redacted, how a flight unfolded, and why a read was refused.

**Key Characteristics:**
- High-contrast, low-noise operational layout
- Cyan and blue reserved for state, action, and hierarchy
- Dense enough for real work, but never metric-wall busy
- Contract-first detail views that make redaction and 403 behavior explicit
- A visible mode shift between Day 1 fixture integrity and Day 2 live reads

## Colors

The palette is restrained and infrastructure-grade: black and blue carry the room, cyan marks truth-bearing actions, and every neutral is tuned for legibility rather than mood.

### Primary
- **Trace Blue** (`#0008f8`): anchors secondary actions, selection states, and cold-path navigation.
- **Vault Cyan** (`#00f8f8`): reserved for the primary call to action, redaction status, and high-signal interface cues.

### Neutral
- **Blackplane** (`#000000`): the product background. Everything floats over this.
- **Night Surface** (`#08101b`): primary panel tone for the explorer shell.
- **Deep Surface** (`#0d1625`): reinforced panel tone for stacked surfaces and emphasis zones.
- **Paper Ink** (`#f8f8f8`): default text color on every operational surface.
- **Muted Ink** (`#f8f8f8ad`): supportive copy, timestamps, metadata, and non-critical labels.

**The Signal Ratio Rule.** Cyan and blue are not decorative paint. If a screen starts feeling neon, the accents are overused.

## Typography

**Display Font:** Segoe UI, Helvetica Neue, Arial, sans-serif  
**Body Font:** Segoe UI, Helvetica Neue, Arial, sans-serif  
**Label/Mono Font:** Consolas, Cascadia Code, Courier New, monospace

**Character:** The shipped stack is judge-safe and OS-present. Segoe UI carries the operational chrome, while mono is reserved for trace identifiers, hashes, and machine-facing fragments. The voice stays calm, firm, and readable at speed.

### Hierarchy
- **Display** (700, `2rem`, line-height `1.1`): welcome-page purpose line only. The brand mark is the hero signal, not a giant marketing headline.
- **Headline** (700, `1.35rem`, line-height `1.15`): panel and section headings inside the explorer.
- **Title** (700, `1.4rem`, line-height `1.2`): panel and section headings.
- **Body** (400, `1rem`, line-height `1.55`): explanatory copy and interface prose. Keep paragraph width under roughly 60ch.
- **Label** (700, `0.8rem`, letter-spacing `0.04em`): eyebrows, chips, metadata labels, and control captions.

**The One Voice Rule.** The official enterprise mark is the welcome hero. Display type only supports it; every other surface stays in product-ui cadence.

## Elevation

Depth is conveyed through tonal layering first and shadow second. Panels float off the black background using dark-surface contrast, then receive one restrained shadow (`0 8px 24px rgba(0,0,0,0.3)`) to separate major shells rather than every nested object.

**The Flat-Until-Needed Rule.** Cards, rows, and badges stay mostly flat. Only top-level panels earn noticeable lift.

## Components

### Buttons
- **Shape:** full-pill (`999px`) buttons with compact horizontal padding (`18px`) and a fixed height (`48px`).
- **Primary:** cyan fill with dark text. This is for moving forward, not for filling space.
- **Secondary:** translucent Trace Blue fill with a blue border. Used for lower-commitment paths like fixture preview.
- **Hover / Focus:** subtle translate-up only. No bounce, no glow theatre.

### Chips / Badges
- **Style:** transparent or near-transparent fills with cyan-border outlines and uppercase label cadence.
- **Purpose:** redaction state, tenant, TTL, and token/session mode.

### Panels / Containers
- **Corner Style:** restrained rounding (`12px` or `14px`), never oversized.
- **Background:** layered dark surfaces with full-border treatment.
- **Internal Padding:** `18px` for explorer shells, `40px` on the welcome panel.
- **Surface Roles:** the list panel, detail panel, and audit strip should feel like one operating surface rather than a stack of unrelated cards.

### Inputs / Fields
- **Style:** border-led controls with transparent backgrounds and light text.
- **Current Signature Field:** the tenant switcher is a pill-wrapped select that reads like operational chrome, not a marketing dropdown.

### Navigation
- **Style:** one welcome route plus one explorer route. The navigation model is direct-path, not multi-page.
- **Trace Navigation:** `/explorer/` is the exported route and `?trace_id=` powers detail selection; do not introduce dynamic `[id]` routes into the exported app.
- **Tenant Context:** in fixture mode the tenant switcher can move between both demo tenants; in live mode the UI should acknowledge that the signed-in Cognito ID token is the real source of tenant truth.

## Intentional Deltas From The Scratchbook Sample

- The official enterprise mark is shipped from the scratchbook asset and used on welcome plus explorer chrome.
- Scratchbook tabs such as `REQUEST`, `RESPONSE`, `TOKENS`, and `METADATA` are intentionally omitted. The judge path stays list → waterfall → RAG hops → governance → audit.
- The explorer summary is one dense operating band, not a KPI-card wall.
- The `VAULT` lockup stays high-contrast against black. Contrast wins over low-contrast blue-on-black branding.
- Decorative body gradients are intentionally removed. The shipped surface is blackplane-first so signal stays on the flight.

## Do's and Don'ts

### Do:
- **Do** keep the product black/blue/cyan and high contrast by default.
- **Do** reserve cyan for primary decisions, confirmation states, and truth-bearing cues like `REDACTED`.
- **Do** keep trace IDs, machine details, and status fragments in mono where they help operators parse faster.
- **Do** show governance inline: 403 chrome, tenant scoping, and TTL should feel first-class.

### Don't:
- **Don't** build a Grafana KPI wall.
- **Don't** make this look like Langfuse, observability theater, or a generic metric-card admin shell.
- **Don't** ship a cream Inter dashboard.
- **Don't** add extra marketing routes, decorative gradients, glassmorphism, or dashboard filler cards.
