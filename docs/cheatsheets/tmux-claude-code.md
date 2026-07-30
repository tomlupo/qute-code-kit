# tmux + Claude Code

Drop-in config: [`claude/terminal/tmux.conf`](../../claude/terminal/tmux.conf).

```bash
cat ~/projects/qute-code-kit/claude/terminal/tmux.conf >> ~/.tmux.conf
tmux source-file ~/.tmux.conf
```

`default-terminal` only applies to *new* sessions; everything else takes effect on source.

## What each line fixes

| Setting | Fixes |
|---|---|
| `allow-passthrough on` | Desktop notifications and the progress bar are swallowed by tmux instead of reaching the outer terminal |
| `extended-keys on` + `xterm*:extkeys` | Shift+Enter submits instead of inserting a newline (tmux can't tell it from plain Enter) |
| `mouse on` | The fullscreen renderer captures the mouse; without tmux mouse mode, raw SGR reports leak into the prompt as garbage text |
| `set-clipboard on` + `clipboard` feature | `/copy` and copy-on-select fail over SSH — Claude Code falls back to OSC 52, which tmux blocks by default |
| `focus-events on` | The TUI can't tell when its pane loses focus |
| `escape-time 0` | Esc chords feel laggy |
| `RGB` feature + `default-terminal tmux-256color` | Washed-out colours, no italics |
| `history-limit 100000` | Shallow scrollback under the classic renderer |

## The mouse-garbage symptom

Strings like this appearing in the Claude Code input box:

```
55;8M;58;9M90;5M5;65;145;70;16M;16M35;73;2M19M;53;29M26M35;61;28MMM1;32M35;68;30M
```

These are SGR mouse reports (`ESC[<btn;col;rowM`). The escape byte is filtered out on
display, leaving the numbers, semicolons and `M`s. Confirm it with tmux's own flags:

```bash
tmux display -p -t <session> \
  'cmd=#{pane_current_command} mouse_any=#{mouse_any_flag} mouse_sgr=#{mouse_sgr_flag} tmux_mouse=#{?mouse,ON,OFF}'
# cmd=claude mouse_any=1 mouse_sgr=1 tmux_mouse=OFF   <- the broken combination
```

**Cause.** Claude Code's `"tui": "fullscreen"` renderer captures mouse events. The
[fullscreen docs](https://code.claude.com/docs/en/fullscreen) require `set -g mouse on`
in tmux — without it tmux forwards the raw reports into the pane, and Claude Code's
input handler doesn't consume them
([#30644](https://github.com/anthropics/claude-code/issues/30644),
[#38810](https://github.com/anthropics/claude-code/issues/38810),
[#23581](https://github.com/anthropics/claude-code/issues/23581)).

**Fix.** `set -g mouse on`. Clear the polluted input box with `Ctrl+U`.

If it persists, opt out of mouse capture on the Claude Code side instead:

| Variable | Effect |
|---|---|
| `CLAUDE_CODE_DISABLE_MOUSE_CLICKS=1` | Keeps wheel scroll; drops click, drag, hover. Needs v2.1.195+ |
| `CLAUDE_CODE_DISABLE_MOUSE=1` | Drops all mouse capture; native terminal selection works again. Takes precedence over the above |

## Other tmux-specific gotchas

- **Flicker.** tmux through the 3.6 series doesn't implement synchronized output, so
  upgrading tmux won't fix it. Use the fullscreen renderer (`/tui fullscreen`) instead.
- **Stale text fragments on Windows Terminal** (or any ConPTY host) in fullscreen mode:
  set `CLAUDE_CODE_ALT_SCREEN_FULL_REPAINT=1`.
- **`/terminal-setup` must run in the host terminal**, not inside tmux — it writes to the
  host terminal's own config file.
- **`tmux -CC` (iTerm2 integration mode)** is incompatible with fullscreen rendering.
  Regular tmux inside iTerm2 is fine.
- **Searching the conversation** under fullscreen: `Ctrl+o` for transcript mode, then `[`
  to dump it into native scrollback where tmux copy mode can see it.

## Verify

```bash
tmux show -gv allow-passthrough   # on
tmux show -sv extended-keys       # on
tmux show -gv mouse               # on
tmux show -gv set-clipboard       # on
tmux show -gv terminal-features   # includes xterm*:extkeys:RGB:clipboard
```

To syntax-check without touching a live session:

```bash
tmux -L cfgtest -f ~/.tmux.conf new-session -d 'sleep 5' && tmux -L cfgtest kill-server
```

## Sources

- [Configure your terminal for Claude Code](https://code.claude.com/docs/en/terminal-config)
- [Fullscreen rendering](https://code.claude.com/docs/en/fullscreen)
- [Environment variables](https://code.claude.com/docs/en/env-vars)
