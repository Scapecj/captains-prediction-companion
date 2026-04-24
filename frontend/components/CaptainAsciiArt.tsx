type CaptainAsciiVariant = 'hero' | 'dashboard' | 'bot-dash' | 'alert' | 'sidebar' | 'home' | 'wordmark'

const ART: Record<CaptainAsciiVariant, string> = {
  hero: String.raw`
                   ╭────────────────╮
               ╭───╯   ▄▄▄▄▄▄▄▄     ╰───╮
            ╭──╯    ╭─█  @    $  █─╮     ╰──╮
         ╭──╯      │  █   ▄▄▄▄   █  │       ╰──╮
       ╭─╯        ╭─│  █  ██████  █  │─╮        ╰─╮
      ╭╯         │  │  ╰─██▀▀██─╯  │  │          ╰╮
     ╭╯          │  ╰──╮   ▀▀▀▀   ╭──╯  │           ╰╮
    ╭╯           │     ╰╮  ▄██▄  ╭╯     │            ╰╮
   ╭╯            ╰╮      ╰╮████╭╯      ╭╯             ╰╮
  ╭╯              ╰╮    ╭╮ ║██║ ╭╭    ╭╯               ╰╮
 ╭╯                 ╰╮  ╭╯╰╮║██║╭╰╮  ╭╯                 ╰╮
╭╯          ⚓        ╰╮╭╯  ╰╯  ╰╯  ╰╮╭╯        ⚔         ╰╮
╰─────────────────────╯╰────────────╯╰────────────────────╯
                      ╱╱            ╲╲
                     ╱╱              ╲╲
`,
  dashboard: String.raw`
      ╔═══════════════════════════╗
      ║   COMMANDER STATE BOARD   ║
      ╠═══════════════════════════╣
      ║      █████████████        ║
      ║    ██╔═════════════╗██    ║
      ║   ██║  @   ▄▄▄   $ ║██    ║
      ║   ██║    ▄██████▄  ║██    ║
      ║   ██║   ╭╮ ████ ╭╮ ║██    ║
      ║   ██║   ╰╯  ▀▀▀▀ ╰╯ ║██    ║
      ║   ██║    ╱╲ ▓▓▓ ╱╲  ║██    ║
      ║   ██╚════╯ ╰─⚓─╯ ╰════╝██   ║
      ║      █████████████        ║
      ╚═══════════════════════════╝
`,
  'bot-dash': String.raw`
      ╔════════════════════════════════╗
      ║    BOT DASH / IRON CAPTAIN    ║
      ╠════════════════════════════════╣
      ║  ╭──────────────────────────╮  ║
      ║  │  ████▄   @  ▄███▄   $   │  ║
      ║  │  █▀▀▀▀▀╲      ╱▀▀▀▀▀█   │  ║
      ║  │  █  ▄▄▄▄╲╭──╮╱▄▄▄▄  █   │  ║
      ║  │  █  ████ ╰╯╭╮╰╯████  █   │  ║
      ║  │  █   ▀▀▀▀  ╰╯  ▀▀▀   █   │  ║
      ║  │  ╰───────╮ ▓▓ ▓▓ ╭────╯   │  ║
      ║  ╰──────────╯╭─⚓─╮╰─────────╯  ║
      ╚════════════════════════════════╝
`,
  alert: String.raw`
      ╔════════════════════════════════════╗
      ║   !!! RED ALERT — IRON CAPTAIN !!! ║
      ╠════════════════════════════════════╣
      ║    ╭──────────────────────────╮    ║
      ║    │  ████▄  @   ▄███▄  $    │    ║
      ║    │  █▀▀▀▀█╲    ╱█▀▀▀▀█     │    ║
      ║    │  █ ▄▄▄█ ╲╭╮╱ █▄▄▄ █     │    ║
      ║    │  █ ████  ╰╯  ████ █     │    ║
      ║    │  █  ▀▀▀   ▄▄▄   ▀▀  █     │    ║
      ║    │  ╰──────╮ ▓▓▓ ╭──────╯    │    ║
      ║    ╰─────────╯╭─⚓─╮╰──────────╯    ║
      ╚════════════════════════════════════╝
`,
  sidebar: String.raw`
    ╭──────╮
   ╭╯ @  $ ╰╮
   │  ▄██▄  │
   │ ▄████▄ │
   │╱ ████ ╲│
   ╰╮╲████╱╭╯
    ╰─╮▀▀╭─╯
      ╰──╯
`,
  home: String.raw`
  ╔════════════════════════════════════════╗
  ║   CAPTAIN'S MENTIONS // BLACK FLAG   ║
  ║   @  evidence-first   $  settlement   ║
  ╠════════════════════════════════════════╣
  ║      ███████████████████████████       ║
  ║   ╭──█  @  ▄▄▄▄▄▄▄  $  █──╮           ║
  ║  ╱   █  ▄██████████▄    █   ╲         ║
  ║ ╱    █ ╭╮  ██████  ╭╮   █    ╲        ║
  ║╱     █ ╰╯  ▀▀▀▀▀▀  ╰╯   █     ╲       ║
  ║     ╱╲      ▄▓▓▓▄      ╱╲      ╲      ║
  ║    ╱__╲____╭─⚓─╮____╱__╲      ╲     ║
  ╚════════════════════════════════════════╝
`,
  wordmark: String.raw`
  ╭────────────────────────────────────────╮
  │   ⚓  CAPTAIN'S MENTIONS               │
  │      BLACK FLAG / EVIDENCE FIRST       │
  ╰────────────────────────────────────────╯
`,
}

const STYLES: Record<CaptainAsciiVariant, string> = {
  hero: 'border-cyan/45 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(0,0,0,0.78))] text-cyan shadow-[0_0_56px_rgba(34,211,238,0.16)]',
  dashboard: 'border-emerald/40 bg-[linear-gradient(180deg,rgba(12,25,20,0.95),rgba(0,0,0,0.75))] text-emerald shadow-[0_0_46px_rgba(16,185,129,0.15)]',
  'bot-dash': 'border-rose/40 bg-[linear-gradient(180deg,rgba(35,8,14,0.96),rgba(0,0,0,0.8))] text-rose shadow-[0_0_46px_rgba(244,63,94,0.15)]',
  alert: 'border-rose/55 bg-[linear-gradient(180deg,rgba(61,11,16,0.98),rgba(0,0,0,0.84))] text-rose shadow-[0_0_54px_rgba(244,63,94,0.22)]',
  sidebar: 'border-cyan/25 bg-[linear-gradient(180deg,rgba(12,18,28,0.92),rgba(0,0,0,0.7))] text-cyan shadow-[0_0_28px_rgba(34,211,238,0.1)]',
  home: 'border-cyan/45 bg-[linear-gradient(180deg,rgba(10,18,26,0.98),rgba(0,0,0,0.82))] text-cyan shadow-[0_0_62px_rgba(34,211,238,0.16)]',
  wordmark: 'border-emerald/35 bg-[linear-gradient(180deg,rgba(11,18,15,0.95),rgba(0,0,0,0.78))] text-emerald shadow-[0_0_40px_rgba(16,185,129,0.15)]',
}

const LABELS: Record<CaptainAsciiVariant, string> = {
  hero: 'Captain close-up',
  dashboard: 'State monitor',
  'bot-dash': 'Automation beast',
  alert: 'Red alert',
  sidebar: 'Captain crest',
  home: 'Home flag',
  wordmark: "Captain's Mentions",
}

export function CaptainAsciiArt({
  variant = 'hero',
  className = '',
}: {
  variant?: CaptainAsciiVariant
  className?: string
}) {
  const isWordmark = variant === 'wordmark'

  return (
    <figure className={`space-y-2 ${className}`.trim()}>
      <figcaption className="text-[10px] uppercase tracking-[0.22em] text-text-muted">
        {LABELS[variant]}
      </figcaption>
      <div className="group relative overflow-hidden rounded-2xl">
        <pre
          aria-hidden="true"
          className={`overflow-x-auto whitespace-pre rounded-2xl border px-4 py-3 font-mono text-[12px] leading-none ${STYLES[variant]} ${isWordmark ? 'tracking-[0.06em]' : ''} animate-captain-flicker xl:[transform-origin:top_right] ${variant === 'sidebar' ? 'scale-[0.9] origin-left' : ''}`}
        >
          {ART[variant]}
        </pre>
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(255,255,255,0.03)_46%,rgba(34,211,238,0.14)_50%,rgba(255,255,255,0.03)_54%,transparent_100%)] opacity-70 mix-blend-screen animate-captain-scanline" />
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-white/5 animate-captain-glow" />
      </div>
    </figure>
  )
}
