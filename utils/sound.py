"""Synthesized sound effects with a floating mute button, built as a Streamlit custom component (v2).

All sounds are generated with the Web Audio API (no audio files, nothing copyrighted).
Other components play a sound with `window.swSound?.play("saber")`.
The hologram sound plays automatically whenever the chat's ".holo-loading" element appears.
The mute choice is remembered per browser in localStorage.
"""
import streamlit as st

_HTML = """
<button class="snd" type="button">
  <svg class="on" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 9v6h4l5 4V5L8 9H4z"/>
    <path class="wave" d="M16 8.5a5 5 0 0 1 0 7"/>
    <path class="wave" d="M18.5 6a8.5 8.5 0 0 1 0 12"/>
  </svg>
  <svg class="off" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 9v6h4l5 4V5L8 9H4z"/>
    <path class="x" d="M16.5 9.5l5 5m0-5l-5 5"/>
  </svg>
</button>
"""

_CSS = """
:host { --accent: #FFE81F; }
.snd {
  position: fixed;
  top: 14px;
  left: 14px;
  z-index: 1000;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
  background: rgba(10, 12, 28, 0.78);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(8px);
  box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 25%, transparent);
  transition: box-shadow .25s, transform .15s, border-color .25s;
}
.snd:hover { box-shadow: 0 0 26px color-mix(in srgb, var(--accent) 55%, transparent); }
.snd:active { transform: scale(0.92); }
.snd:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.snd svg { width: 22px; height: 22px; fill: currentColor; stroke: currentColor; stroke-width: 0; }
.snd .wave, .snd .x { fill: none; stroke-width: 2; stroke-linecap: round; }
.snd .off { display: none; }
.snd.muted { border-color: rgba(255, 255, 255, 0.18); box-shadow: none; color: #9AA3C7; }
.snd.muted .on { display: none; }
.snd.muted .off { display: block; }
.snd:not(.muted) .wave { animation: pulse 2.2s ease-in-out infinite; }
.snd:not(.muted) .wave + .wave { animation-delay: .3s; }
@keyframes pulse { 50% { opacity: .35; } }
@media (max-width: 760px) {
  /* smaller and softer on phones, so it covers as little content as possible */
  .snd { top: 8px; left: 8px; width: 36px; height: 36px; opacity: 0.8; }
  .snd svg { width: 18px; height: 18px; }
}
@media (prefers-reduced-motion: reduce) { .wave { animation: none !important; } }
"""

_JS = """
const STORAGE_KEY = "sw-sound-muted"

function readMuted() {
  try { return localStorage.getItem(STORAGE_KEY) === "1" } catch (e) { return false }
}
function saveMuted(value) {
  try { localStorage.setItem(STORAGE_KEY, value ? "1" : "0") } catch (e) {}
}

// One shared sound engine for the whole page
function createEngine() {
  let ctx = null
  let master = null
  let noiseBuffer = null
  const engine = { muted: readMuted() }

  const audio = () => {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext
      if (!AC) return null
      ctx = new AC()
      master = ctx.createGain()
      master.gain.value = 0.32
      master.connect(ctx.destination)
    }
    if (ctx.state === "suspended") ctx.resume()
    return ctx
  }
  engine.unlock = audio

  const noise = () => {
    if (!noiseBuffer) {
      noiseBuffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate)
      const d = noiseBuffer.getChannelData(0)
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1
    }
    const src = ctx.createBufferSource()
    src.buffer = noiseBuffer
    return src
  }

  const envelope = (gainNode, t, attack, peak, release) => {
    gainNode.gain.setValueAtTime(0.0001, t)
    gainNode.gain.exponentialRampToValueAtTime(peak, t + attack)
    gainNode.gain.exponentialRampToValueAtTime(0.0001, t + attack + release)
  }

  const tone = (type, from, to, start, dur, peak) => {
    const t = ctx.currentTime + start
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.type = type
    o.frequency.setValueAtTime(from, t)
    o.frequency.exponentialRampToValueAtTime(to, t + dur)
    envelope(g, t, 0.008, peak, dur)
    o.connect(g).connect(master)
    o.start(t)
    o.stop(t + dur + 0.05)
  }

  const sounds = {
    // Energy blade igniting: rising buzz with a crackle, settling into a hum
    saber() {
      const t = ctx.currentTime
      const filter = ctx.createBiquadFilter()
      filter.type = "lowpass"
      filter.frequency.setValueAtTime(300, t)
      filter.frequency.exponentialRampToValueAtTime(2400, t + 0.25)
      filter.frequency.exponentialRampToValueAtTime(700, t + 1.3)
      const g = ctx.createGain()
      g.gain.setValueAtTime(0.0001, t)
      g.gain.exponentialRampToValueAtTime(0.55, t + 0.06)
      g.gain.exponentialRampToValueAtTime(0.25, t + 0.4)
      g.gain.exponentialRampToValueAtTime(0.0001, t + 1.4)
      filter.connect(g).connect(master)
      for (const [type, f] of [["sawtooth", 90], ["sawtooth", 91.5], ["square", 45]]) {
        const o = ctx.createOscillator()
        o.type = type
        o.frequency.setValueAtTime(f * 0.6, t)
        o.frequency.exponentialRampToValueAtTime(f * 1.4, t + 0.2)
        o.frequency.exponentialRampToValueAtTime(f, t + 0.5)
        o.connect(filter)
        o.start(t)
        o.stop(t + 1.45)
      }
      const n = noise()
      const nf = ctx.createBiquadFilter()
      nf.type = "bandpass"
      nf.frequency.value = 3200
      const ng = ctx.createGain()
      envelope(ng, t, 0.005, 0.35, 0.18)
      n.connect(nf).connect(ng).connect(master)
      n.start(t)
      n.stop(t + 0.3)
    },
    // Air sweep, used for flipping the card
    whoosh() {
      const t = ctx.currentTime
      const n = noise()
      const f = ctx.createBiquadFilter()
      f.type = "bandpass"
      f.Q.value = 1.4
      f.frequency.setValueAtTime(350, t)
      f.frequency.exponentialRampToValueAtTime(2200, t + 0.18)
      f.frequency.exponentialRampToValueAtTime(500, t + 0.4)
      const g = ctx.createGain()
      envelope(g, t, 0.06, 0.6, 0.36)
      n.connect(f).connect(g).connect(master)
      n.start(t)
      n.stop(t + 0.5)
    },
    // Short UI confirmation, used for picking a character
    select() {
      tone("sine", 620, 930, 0, 0.09, 0.35)
      tone("triangle", 930, 1400, 0.07, 0.12, 0.25)
    },
    // Hologram transmission: static burst and a run of droid-style chirps
    holo() {
      const t = ctx.currentTime
      const n = noise()
      const f = ctx.createBiquadFilter()
      f.type = "highpass"
      f.frequency.value = 2500
      const g = ctx.createGain()
      envelope(g, t, 0.01, 0.12, 0.35)
      n.connect(f).connect(g).connect(master)
      n.start(t)
      n.stop(t + 0.4)
      let start = 0.12
      for (let i = 0; i < 5; i++) {
        const from = 900 + Math.random() * 1500
        const to = 900 + Math.random() * 1500
        const dur = 0.045 + Math.random() * 0.06
        tone("sine", from, to, start, dur, 0.22)
        start += dur + 0.02 + Math.random() * 0.04
      }
    },
    // Played when sound is switched back on
    toggle() {
      tone("sine", 520, 780, 0, 0.12, 0.3)
    },
  }

  engine.play = (name) => {
    if (engine.muted || !sounds[name]) return
    if (!audio()) return
    try { sounds[name]() } catch (e) {}
  }

  // Browsers allow audio only after a user gesture: unlock on the first click or key press
  const unlock = () => {
    if (!engine.muted) audio()
  }
  document.addEventListener("pointerdown", unlock, { capture: true })
  document.addEventListener("keydown", unlock, { capture: true })

  // Play the hologram sound whenever a chat answer starts loading
  new MutationObserver((records) => {
    for (const r of records) {
      for (const node of r.addedNodes) {
        if (node.nodeType !== 1) continue
        if (node.matches?.(".holo-loading") || node.querySelector?.(".holo-loading")) {
          engine.play("holo")
          return
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true })

  return engine
}

export default function (component) {
  const { data, parentElement } = component
  const button = parentElement.querySelector(".snd")
  if (!button) return

  if (!window.swSound) window.swSound = createEngine()
  const engine = window.swSound

  button.style.setProperty("--accent", (data && data.accent) || "#FFE81F")

  const render = () => {
    button.classList.toggle("muted", engine.muted)
    const label = engine.muted ? "הפעלת צלילים" : "השתקת צלילים"
    button.setAttribute("aria-label", label)
    button.title = label
    button.setAttribute("aria-pressed", engine.muted ? "true" : "false")
  }
  render()

  button.onclick = () => {
    engine.muted = !engine.muted
    saveMuted(engine.muted)
    render()
    engine.play("toggle")
  }
}
"""

_SOUND = st.components.v2.component(
    "sw_sound_effects",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def sound_effects(accent: str, *, key: str = "sound_effects"):
    """Mount the sound engine and its floating mute button (top-left corner)."""
    return _SOUND(data={"accent": accent}, key=key)
