# NetWeather UI Guidelines

This file is the UI contract for every web screen.

## 1. Typography

- Minimum rendered text size: **10 px**.
- Body/control text should normally be 11–14 px.
- Headings must form a consistent hierarchy.
- Do not solve density problems by shrinking text below the minimum.
- One global font stack is used across Overview, tables, dialogs, settings and diagnostics.

## 2. Density

NetWeather is an information dashboard.

Prefer:
- useful metrics;
- compact groups;
- clear hierarchy;
- aligned columns;
- predictable panel sizes.

Avoid:
- oversized empty surfaces;
- decorative cards with no information;
- forcing the whole Overview into one viewport by shrinking or clipping useful information;
- nested vertical scroll areas for primary dashboard content. Use natural page scrolling when it
  keeps charts, resource cards and problem rows readable.

## 3. Groups

Groups are a first-class model.

Every resource flow must preserve group context:
- add;
- edit;
- filter;
- pin to Overview;
- catalog;
- reports.

Resources from the curated catalog must not be duplicated across groups.

Basic resource addition is a public action. Owner authentication must only be requested for
management actions or capability-gated checks; the add flow must not redirect a viewer to login.

## 4. Capability-aware UI

If functionality is unavailable, hide it instead of showing a dead panel.

Examples:
- no domestic probe → no “Российский контур” KPI;
- no user/browser probe → no “Моя сеть” KPI;
- no geodata → no outage map;
- no traceroute capability → no traceroute action.

The surrounding layout must reclaim the space.

## 5. Buttons

Every button must have:
- normal state;
- hover state;
- visible keyboard focus;
- disabled state;
- busy state for async work.

Rules:
- a busy button cannot be double-submitted;
- destructive action uses danger styling;
- icon-only buttons require `title` and accessible label;
- labels describe the action, not implementation details.

## 6. Dialogs

All dialogs follow one behavior contract:

- open with focus on the first useful control;
- `Escape` closes unless a destructive operation is actively committing;
- clicking the backdrop closes non-destructive dialogs;
- close button is always in the same top-right location;
- focus returns to the element that opened the dialog;
- forms support Enter where it is unambiguous;
- async submit disables controls until completion;
- errors stay inside the dialog context where possible.

## 7. Keyboard

Required shortcuts:

- `Ctrl/Cmd + K` — global search;
- `Escape` — close search / active dialog / expanded chart in that order;
- `Enter` — activate focused result or primary form action;
- arrow keys — move through global search results.

Visible focus must never be removed.

## 8. Loading / empty / error

A surface must never look “working” when data is unavailable.

- **Loading:** skeleton/spinner + explicit label when operation is user-triggered.
- **Empty:** explain why there is no content and provide the next action.
- **Error:** show what failed and allow retry where meaningful.
- **Stale:** show age of last good data.

## 9. Tables

- column labels remain visible when panel scrolls;
- entire row can open details when appropriate;
- row actions do not accidentally trigger row navigation;
- numeric metrics align consistently;
- long URLs/names truncate visually but remain available via title/detail.

## 10. Accessibility

- semantic buttons, inputs and dialogs;
- icon buttons have accessible names;
- status is not encoded by color alone;
- `:focus-visible` is obvious;
- reduced-motion preference is respected;
- contrast must remain readable in both themes.

## 11. Overview

The Overview answers, without navigation:

1. Is the network healthy?
2. Which important resources are affected?
3. Is the problem global, regional or local?
4. Are there active incidents?
5. Where should the user click for evidence?

Pinned resources: maximum 6.

The Overview must remain customizable without producing empty holes.

Operational hierarchy is fixed even when optional capabilities are hidden:

1. current health, freshness and four core KPIs;
2. time-series evidence and recent events;
3. pinned resources;
4. a problem-first resource table and capability-specific diagnostics.

The resource table on Overview is a bounded summary, not a duplicate of Monitoring. It shows at
most 8 rows, sorts items requiring attention first and offers an explicit problem-only filter.
