import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Board, Short } from '../types'

// ── YOUR SETTINGS ────────────────────────────────────────────────────────────
// The folder that holds shorts.json and shorts_board.py (use double backslashes on Windows).
const BOARD_DIR = 'C:\\path\\to\\your\\content'
// What the panel runs to read your schedule. Python 3 on PATH ('python3' on macOS).
const BOARD_CMD = ['python', 'shorts_board.py']
const POST_TIME = '7 PM'                       // shown under tomorrow's date
const FILM_HINT = 'Film it today.'             // shown when tomorrow's short isn't recorded
// ─────────────────────────────────────────────────────────────────────────────

const PANE = 'tomorrows-short'
const TITLE = "Tomorrow's short"
const PINK = '#FF1564'
const EVERY_MS = 5 * 60 * 1000

// The pipeline, in order. Everything from `recorded` on means it's filmed.
const STAGES = ['scripted', 'recorded', 'production', 'review', 'ready', 'scheduled', 'published']
const RECORDED_FROM = STAGES.indexOf('recorded')
const DEAD = ['expired', 'retired', 'killed']

// Change the tag when Board's fields change: it drops what an older version stored.
const board = atom({ plugin: 'tomorrows-short', key: 'board' } as const, null, {
  shape: 'board-1',
})

// "2026-11-01" -> "2026-11-02", in plain calendar days (no timezone drift).
const nextDay = (iso: string) => {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString().slice(0, 10)
}

const isRecorded = (s: Short) => STAGES.indexOf(s.stage) >= RECORDED_FROM

// Shorts slotted for tomorrow, the furthest along first.
const forTomorrow = (b: Board) =>
  b.shorts
    .filter(s => s.post_date === nextDay(b.today) && !DEAD.includes(s.stage))
    .sort((a, z) => STAGES.indexOf(z.stage) - STAGES.indexOf(a.stage))

// Runs BOARD_CMD (shorts_board.py prints shorts.json in the shape types/index.d.ts describes) and keeps the result.
async function refresh($: EngineInterface) {
  const checkedAt = new Date().toTimeString().slice(0, 5)
  try {
    const { exitCode, stdout, stderr } = await $.process.run(BOARD_CMD, { cwd: BOARD_DIR, timeoutMs: 20_000 })
    if (exitCode !== 0) throw new Error(stderr.trim().split('\n').pop() || `exit ${exitCode}`)
    const data = JSON.parse(stdout)
    await update($, board, () => ({
      checkedAt,
      today: data.today,
      buffer: data.buffer,
      bufferMin: data.buffer_min,
      shorts: data.shorts,
    }))
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    await update($, board, old => ({
      ...(old ?? { today: '', buffer: 0, bufferMin: 0, shorts: [] }),
      checkedAt,
      error,
    }))
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'tomorrow',
      description: "Open the Tomorrow's short panel and re-read your schedule",
    })
    void $.ui.open({ id: PANE, title: TITLE })
    void refresh($)
    $.clock.every(EVERY_MS, () => void refresh($))

    return next(e)
  })

  on('command.run', { command: 'tomorrow' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    await refresh($)
    const b = await read($, board)
    const s = b && forTomorrow(b)[0]

    return {
      text: s
        ? `Tomorrow: ${s.id} ${s.title} — ${isRecorded(s) ? 'recorded' : 'NOT recorded yet'} (${s.stage})`
        : 'Nothing slotted for tomorrow.',
    }
  })

  // If Claude touches your schedule in this session, the panel updates right away.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    const cmd = (e as { command?: unknown }).command
    if (typeof cmd === 'string' && /shorts\.json|shorts_board/.test(cmd)) void refresh($)

    return ran
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const b = await read($, board)

    if (!b || !b.today) {
      return (
        <Box flexDirection="column">
          <Text dimColor>{b?.error ? `Couldn't read your schedule: ${b.error}` : 'Reading your schedule…'}</Text>
          <Button onPress={() => void refresh($)}>Refresh</Button>
        </Box>
      )
    }

    const tomorrow = nextDay(b.today)
    const list = forTomorrow(b)
    const toRecord = b.shorts
      .filter(s => s.stage === 'scripted' && s.post_date && s.post_date > tomorrow)
      .sort((a, z) => (a.post_date ?? '').localeCompare(z.post_date ?? ''))

    return (
      <Box flexDirection="column" gap={1}>
        <Text dimColor>{tomorrow} · {POST_TIME}</Text>

        {list.length === 0 && (
          <Box flexDirection="column">
            <Text bold color="warning">Nothing slotted for tomorrow</Text>
            <Text dimColor>Add a short to shorts.json with post_date {tomorrow}.</Text>
          </Box>
        )}

        {list.map(s => {
          const at = STAGES.indexOf(s.stage)
          const done = isRecorded(s)
          return (
            <Box flexDirection="column">
              <Text bold>{s.id} · {s.title}</Text>
              {s.pillar ? <Text dimColor>{s.pillar}</Text> : null}
              <Text bold color={done ? 'success' : PINK}>
                {done ? '✓ Recorded' : '● Not recorded yet'}
              </Text>
              <Text>
                {STAGES.map((_, i) => (i <= at ? '●' : '○')).join(' ')}  {s.stage}
              </Text>
              {!done && <Text dimColor>{FILM_HINT}</Text>}
              {s.fresh_until ? <Text dimColor>Fresh until {s.fresh_until}</Text> : null}
            </Box>
          )
        })}

        <Text color={b.buffer < b.bufferMin ? 'warning' : 'subtle'}>
          Buffer: {b.buffer} day(s) scheduled ahead{b.buffer < b.bufferMin ? ` (under ${b.bufferMin})` : ''}
        </Text>

        {toRecord.length > 0 && (
          <Box flexDirection="column">
            <Text bold>Still to record after that</Text>
            {toRecord.slice(0, 4).map(s => (
              <Text dimColor>{s.post_date} · {s.id} {s.title}</Text>
            ))}
          </Box>
        )}

        <Box flexDirection="column">
          <Text dimColor>Checked {b.checkedAt}{b.error ? ` · last read failed: ${b.error}` : ''}</Text>
          <Button onPress={() => void refresh($)}>Refresh</Button>
        </Box>
      </Box>
    )
  })
}
