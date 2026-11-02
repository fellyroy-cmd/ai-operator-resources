// One short as `hq_board.py shorts --json` prints it.
export type Short = {
  id: string
  title: string
  stage: string
  post_date: string | null
  fresh_until: string | null
  pillar: string | null
  lane: string | null
}

// The last read of the board. `error` is set when the read failed.
export type Board = {
  checkedAt: string
  today: string
  buffer: number
  bufferMin: number
  shorts: Short[]
  error?: string
}

declare module 'claude-code' {
  interface PluginState {
    'tomorrows-short': { board: Shaped<Board | null> }
  }
}
