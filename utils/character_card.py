"""Animated Star Wars character card, built as a Streamlit custom component (v2).

The card shows the character's name and stats, a 3D tilt/flip image card
(real photo on the front, hand-drawn cartoon on the back) and a
"new character" button that sends a trigger back to Python.
"""
from collections.abc import Callable

import streamlit as st

_HTML = """
<div class="sw-card" dir="rtl">
  <div class="sw-loading" aria-hidden="true">
    <div class="sw-hyperspace"></div>
    <div class="sw-loading-text">קופצים להיפר־חלל...</div>
  </div>
  <div class="sw-info">
    <div class="sw-meta">
      <span class="sw-side"><span class="sw-dot"></span><span class="sw-side-label"></span></span>
      <span class="sw-kicker"></span>
    </div>
    <h2 class="sw-name"></h2>
    <div class="sw-stats"></div>
    <button class="sw-new" type="button">
      <span class="sw-saber"></span>
      <span class="sw-new-label">טען דמות חדשה</span>
    </button>
  </div>
  <div class="sw-visual">
    <div class="sw-tilt">
      <div class="sw-flipper">
        <div class="sw-face sw-front"><img alt="" /></div>
        <div class="sw-face sw-back"><img alt="" /></div>
      </div>
    </div>
    <div class="sw-hint"></div>
  </div>
</div>
"""

_CSS = """
:host {
  --gold: #FFE81F;
  --accent: #4BB3FD;
  --blue: #4BB3FD;
  --red: #FF3B3B;
  --panel: rgba(17, 20, 42, 0.72);
  --edge: rgba(124, 196, 255, 0.22);
  --text: #E8ECF5;
  --muted: #9AA3C7;
  display: block;
  font-family: "Heebo", system-ui, sans-serif;
  color: var(--text);
}

.sw-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 2rem;
  align-items: center;
  padding: 2rem;
  border-radius: 24px;
  background:
    radial-gradient(120% 80% at 100% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 60%),
    radial-gradient(90% 70% at 0% 100%, rgba(255, 232, 31, 0.10), transparent 60%),
    var(--panel);
  border: 1px solid color-mix(in srgb, var(--accent) 32%, transparent);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.55), 0 0 60px color-mix(in srgb, var(--accent) 12%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: border-color .8s, box-shadow .8s;
  backdrop-filter: blur(14px);
  overflow: hidden;
}

/* moving holographic sheen across the card */
.sw-card::before {
  content: "";
  position: absolute;
  inset: -50%;
  background: linear-gradient(115deg, transparent 40%, color-mix(in srgb, var(--accent) 9%, transparent) 50%, transparent 60%);
  animation: sheen 7s linear infinite;
  pointer-events: none;
}
@keyframes sheen {
  from { transform: translateX(-30%); }
  to { transform: translateX(30%); }
}

/* ---------- info column ---------- */
.sw-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.sw-side {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
}
.sw-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent);
  animation: blink 2s ease-in-out infinite;
}
@keyframes blink { 50% { opacity: 0.35; } }
.sw-kicker {
  font-size: 0.85rem;
  letter-spacing: 0.25em;
  color: var(--accent);
  text-transform: uppercase;
  font-family: "Orbitron", "Heebo", sans-serif;
  opacity: 0.85;
}
.sw-name {
  margin: 0.35rem 0 1.25rem;
  font-family: "Orbitron", "Heebo", sans-serif;
  font-weight: 700;
  font-size: clamp(1.8rem, 4vw, 3.2rem);
  line-height: 1.1;
  direction: ltr;
  text-align: right;
  /* lightsaber look: white core, colored glow */
  color: #fff;
  text-shadow:
    0 0 4px rgba(255, 255, 255, 0.8),
    0 0 14px var(--accent),
    0 0 34px var(--accent),
    0 0 70px color-mix(in srgb, var(--accent) 55%, transparent);
}

.sw-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}
.sw-stat {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.85rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  opacity: 0;
  transform: translateY(12px);
  animation: rise 0.55s cubic-bezier(.2, .8, .2, 1) forwards;
  transition: border-color .25s, background .25s, transform .25s;
}
.sw-stat:last-child:nth-child(odd) { grid-column: 1 / -1; }
@media (hover: hover) {
  .sw-stat:hover {
    border-color: color-mix(in srgb, var(--accent) 60%, transparent);
    background: color-mix(in srgb, var(--accent) 9%, transparent);
  }
}
.sw-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 10px;
  font-size: 1.05rem;
  background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 32%, transparent), rgba(255, 255, 255, 0.04));
}
.sw-stat-text { min-width: 0; }
.sw-label { font-size: 0.78rem; color: var(--muted); }
.sw-value {
  font-size: 1rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

@keyframes rise {
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- lightsaber button ---------- */
.sw-new {
  position: relative;
  margin-top: 1.5rem;
  width: 100%;
  padding: 0.95rem 1.2rem;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--accent) 60%, transparent);
  background: color-mix(in srgb, var(--accent) 9%, transparent);
  color: #fff;
  font: 700 1.05rem "Heebo", sans-serif;
  cursor: pointer;
  overflow: hidden;
  transition: transform .15s, box-shadow .3s, background .3s;
}
@media (hover: hover) {
  .sw-new:hover {
    background: color-mix(in srgb, var(--accent) 18%, transparent);
    box-shadow: 0 0 24px color-mix(in srgb, var(--accent) 50%, transparent);
  }
  .sw-new:hover .sw-saber { width: 100%; }
}
.sw-new:active { transform: scale(0.98); }
.sw-new:focus-visible { outline: 2px solid var(--gold); outline-offset: 3px; }
.sw-saber {
  position: absolute;
  bottom: 0;
  right: 0;
  height: 3px;
  width: 0;
  border-radius: 3px;
  background: #fff;
  box-shadow: 0 0 6px #fff, 0 0 12px var(--accent), 0 0 22px var(--accent);
  transition: width .45s cubic-bezier(.2, .8, .2, 1);
}
.sw-new:active .sw-saber { width: 100%; }
.sw-new-label { position: relative; }

/* ---------- image flip card ---------- */
.sw-visual {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}
.sw-tilt {
  /* also limited by screen height, so the whole image fits on a phone held sideways */
  width: min(100%, 340px, 52vh);
  aspect-ratio: 3 / 4;
  perspective: 1200px;
  cursor: pointer;
}
.sw-flipper {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.8s cubic-bezier(.2, .8, .2, 1);
  transform: rotateX(var(--rx, 0deg)) rotateY(calc(var(--ry, 0deg) + var(--flip, 0deg)));
}
.sw-flipper.flipped { --flip: 180deg; }
.sw-flipper.tilting { transition: transform 0.12s linear; }
.sw-face {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  overflow: hidden;
  backface-visibility: hidden;
  background: linear-gradient(160deg, #1b2048, #0a0c1c);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6), 0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
}
.sw-face::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--gx, 50%) var(--gy, 30%), rgba(255, 255, 255, 0.22), transparent 55%);
  mix-blend-mode: overlay;
  pointer-events: none;
}
.sw-back { transform: rotateY(180deg); }
.sw-face img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
  display: block;
}
.sw-hint {
  font-size: 0.85rem;
  color: var(--muted);
}

/* ---------- hyperspace loading overlay ---------- */
.sw-loading {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: grid;
  place-items: center;
  background: rgba(3, 4, 12, 0.88);
  opacity: 0;
  pointer-events: none;
  transition: opacity .25s;
}
.sw-card.loading .sw-loading { opacity: 1; pointer-events: auto; }
.sw-hyperspace {
  position: absolute;
  inset: -40%;
  background: repeating-conic-gradient(from 0deg,
    transparent 0deg 3deg,
    rgba(190, 225, 255, 0.85) 3deg 3.25deg,
    transparent 3.25deg 7deg);
  -webkit-mask: radial-gradient(circle, transparent 6%, #000 22%, transparent 70%);
          mask: radial-gradient(circle, transparent 6%, #000 22%, transparent 70%);
  animation: warp 0.9s cubic-bezier(.5, 0, .9, .5) infinite;
}
@keyframes warp {
  from { transform: scale(0.35); opacity: 0.2; }
  60% { opacity: 1; }
  to { transform: scale(1.6); opacity: 0; }
}
.sw-loading-text {
  position: relative;
  font-family: "Orbitron", "Heebo", sans-serif;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #fff;
  text-shadow: 0 0 16px var(--accent);
}

/* entrance animation for a new character */
.sw-card.enter .sw-name { animation: glowIn 0.8s ease-out both; }
.sw-card.enter .sw-tilt { animation: popIn 0.8s cubic-bezier(.2, .8, .2, 1) both; }
@keyframes glowIn {
  from { opacity: 0; letter-spacing: 0.3em; filter: blur(6px); }
  to { opacity: 1; letter-spacing: normal; filter: none; }
}
@keyframes popIn {
  from { opacity: 0; transform: scale(0.85) rotateY(-25deg); }
  to { opacity: 1; transform: none; }
}

@media (max-width: 760px) {
  .sw-card {
    grid-template-columns: 1fr;
    padding: 1.25rem;
    gap: 1.5rem;
  }
  .sw-visual { order: -1; }
  .sw-tilt { width: min(100%, 240px, 52vh); }
  .sw-stats { grid-template-columns: 1fr 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .sw-stat { opacity: 1; transform: none; }
}
"""

_JS = """
const instances = new WeakMap()

function setImage(img, src, onFail) {
  img.onerror = onFail
  if (img.getAttribute("src") !== src) img.setAttribute("src", src)
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const card = parentElement.querySelector(".sw-card")
  if (!card || !data) return

  let state = instances.get(parentElement)
  if (!state) {
    state = { id: null }
    instances.set(parentElement, state)
  }

  const flipper = card.querySelector(".sw-flipper")
  const tilt = card.querySelector(".sw-tilt")
  const hint = card.querySelector(".sw-hint")
  const frontImg = card.querySelector(".sw-front img")
  const backImg = card.querySelector(".sw-back img")
  const hasReal = Boolean(data.real_image)
  const hasCartoon = Boolean(data.cartoon_image)
  const canFlip = hasReal && hasCartoon

  // A new character arrived: rebuild content and play the entrance animation
  if (state.id !== data.id) {
    state.id = data.id
    card.classList.remove("loading", "enter")
    void card.offsetWidth
    card.classList.add("enter")

    card.style.setProperty("--accent", data.accent || "#4BB3FD")
    card.querySelector(".sw-side-label").textContent = data.side || ""
    card.querySelector(".sw-kicker").textContent = data.kicker || ""
    card.querySelector(".sw-name").textContent = data.name || ""

    const stats = card.querySelector(".sw-stats")
    stats.replaceChildren()
    ;(data.stats || []).forEach((s, i) => {
      const el = document.createElement("div")
      el.className = "sw-stat"
      el.style.animationDelay = `${0.15 + i * 0.07}s`
      const icon = document.createElement("div")
      icon.className = "sw-icon"
      icon.textContent = s.icon
      const text = document.createElement("div")
      text.className = "sw-stat-text"
      const label = document.createElement("div")
      label.className = "sw-label"
      label.textContent = s.label
      const value = document.createElement("div")
      value.className = "sw-value"
      value.textContent = s.value
      text.append(label, value)
      el.append(icon, text)
      stats.append(el)
    })

    flipper.classList.remove("flipped")
    frontImg.alt = `תמונה של ${data.name}`
    backImg.alt = `ציור של ${data.name}`
  }

  const showOnlyCartoon = () => {
    // Real photo is missing or broken: show the cartoon on the front instead
    if (hasCartoon) setImage(frontImg, data.cartoon_image, null)
    state.canFlip = false
    hint.textContent = ""
  }

  state.canFlip = canFlip
  if (hasReal) {
    setImage(frontImg, data.real_image, showOnlyCartoon)
  } else {
    showOnlyCartoon()
  }
  if (hasCartoon) setImage(backImg, data.cartoon_image, null)
  hint.textContent = state.canFlip ? "לחצו על התמונה כדי לראות את הציור" : ""

  // 3D tilt that follows the pointer
  tilt.onpointermove = (e) => {
    if (e.pointerType !== "mouse") return  // on touch screens a finger drag means scrolling
    const r = tilt.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width
    const y = (e.clientY - r.top) / r.height
    flipper.classList.add("tilting")
    flipper.style.setProperty("--ry", `${(x - 0.5) * 18}deg`)
    flipper.style.setProperty("--rx", `${(0.5 - y) * 14}deg`)
    flipper.style.setProperty("--gx", `${x * 100}%`)
    flipper.style.setProperty("--gy", `${y * 100}%`)
  }
  tilt.onpointerleave = tilt.onpointercancel = () => {
    flipper.classList.remove("tilting")
    flipper.style.setProperty("--rx", "0deg")
    flipper.style.setProperty("--ry", "0deg")
  }
  tilt.onclick = () => {
    if (!state.canFlip) return
    flipper.classList.remove("tilting")
    flipper.classList.toggle("flipped")
    window.swSound?.play("whoosh")
  }

  card.querySelector(".sw-new").onclick = () => {
    card.classList.add("loading")
    window.swSound?.play("saber")
    setTriggerValue("new_character", Date.now())
  }
}
"""

_CHARACTER_CARD = st.components.v2.component(
    "sw_character_card",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def character_card(
    *,
    char_id: int,
    name: str,
    kicker: str,
    side: str,
    accent: str,
    stats: list[dict[str, str]],
    real_image: str | None,
    cartoon_image: str | None,
    on_new_character: Callable[[], None],
    key: str = "character_card",
):
    """Render the character card. `on_new_character` runs when the user asks for a new character."""
    return _CHARACTER_CARD(
        data={
            "id": char_id,
            "name": name,
            "kicker": kicker,
            "side": side,
            "accent": accent,
            "stats": stats,
            "real_image": real_image or "",
            "cartoon_image": cartoon_image or "",
        },
        key=key,
        on_new_character_change=on_new_character,
    )
