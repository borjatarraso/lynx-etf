# Run modes

`lynx-etf` exposes one analysis pipeline through four front-ends. All of them
call `lynx_etf.core.analyzer.run_full_analysis` (or `run_progressive_analysis`)
— they differ only in presentation and interaction.

| Mode | Flag | Front-end | Module |
|------|------|-----------|--------|
| Console (default) | *(none)* | one-shot Rich report | `display.py` |
| Interactive REPL | `-i` | prompt loop | `interactive.py` |
| Textual TUI | `-tui` | full-screen terminal UI | `tui/app.py` |
| Tkinter GUI | `-x` | desktop window | `gui/app.py` |

## Console

```bash
lynx-etf -p SPY            # cache-first analysis
lynx-etf -p QQQ --refresh  # force fresh fetch
lynx-etf -p -s "world equity"   # search
lynx-etf --explain expense_ratio  # explain a metric (no network)
```

Renders the full report once via `display.render_full_report` and exits.

## Interactive (`-i`)

A Rich-styled REPL (`interactive.run_interactive`) supporting `analyze`,
`refresh`, `search`, `cache`, `drop-cache`, `explain`, `explain-all`, `about`,
`help`, `quit`. It reuses the CLI sub-command functions, so CLI and REPL stay in
sync.

## TUI (`-tui`)

A Textual app (`tui.app.run_tui`) with keyboard navigation, an About modal, and
Suite-wide theme cycling (`tui/themes.py`).

## GUI (`-x`)

A Tkinter window (`gui.app.run_gui`) with search, results panes, export, and
theme cycling.

## Production vs testing

The `-p` flag selects the production cache (`data/`); without it the tools use
the isolated `data_test/` cache. See [CACHING.md](CACHING.md).
