"""Scrollable character gallery, built as a Streamlit custom component (v2).

Shows every character as a thumbnail in a horizontal strip (drag, wheel or arrows to scroll),
with a search box and a "surprise me" button. Selecting a character sends a trigger to Python.
"""
from collections.abc import Callable

import streamlit as st

_HTML = """
<section class="g" dir="rtl">
  <div class="g-head">
    <div class="g-title">בחרו דמות <span class="g-count"></span></div>
    <div class="g-tools">
      <label class="g-search">
        <span aria-hidden="true">⌕</span>
        <input type="search" placeholder="חיפוש דמות..." aria-label="חיפוש דמות" />
      </label>
      <button class="g-random" type="button">🎲 הפתעה</button>
    </div>
  </div>
  <div class="g-rail">
    <button class="g-arrow g-prev" type="button" aria-label="הקודם">›</button>
    <div class="g-strip" role="list"></div>
    <button class="g-arrow g-next" type="button" aria-label="הבא">‹</button>
  </div>
  <div class="g-empty" hidden>לא נמצאה דמות בשם הזה</div>
</section>
"""

_CSS = """
:host {
  display: block;
  font-family: "Heebo", system-ui, sans-serif;
  color: #E8ECF5;
  --accent: #FFE81F;
}
.g-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.6rem;
}
.g-title { font-weight: 800; font-size: 1.15rem; }
.g-count { font-weight: 400; color: #9AA3C7; font-size: 0.9rem; }
.g-tools { display: flex; gap: 0.5rem; align-items: center; }
.g-search {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #9AA3C7;
  transition: border-color .2s, box-shadow .2s;
}
.g-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 35%, transparent);
}
.g-search input {
  width: 9.5rem;
  border: 0;
  outline: 0;
  background: transparent;
  color: #E8ECF5;
  font: inherit;
}
.g-random {
  padding: 0.45rem 0.95rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: #fff;
  font: 600 0.92rem "Heebo", sans-serif;
  cursor: pointer;
  transition: box-shadow .2s, transform .15s;
}
.g-random:hover { box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 45%, transparent); }
.g-random:active { transform: scale(0.96); }

.g-rail { position: relative; }
.g-strip {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scroll-snap-type: x proximity;
  scrollbar-width: none;
  padding: 0.6rem 0.4rem 0.9rem;
  cursor: grab;
  -webkit-mask: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent);
          mask: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent);
}
.g-strip::-webkit-scrollbar { display: none; }
.g-strip.dragging { cursor: grabbing; scroll-snap-type: none; }
.g-strip.dragging .g-item { pointer-events: none; }

.g-item {
  --c: #FFE81F;
  flex: none;
  width: 88px;
  scroll-snap-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
  transition: transform .25s cubic-bezier(.2, .8, .2, 1), opacity .25s;
}
.g-item[hidden] { display: none; }
.g-thumb {
  position: relative;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  padding: 3px;
  background: conic-gradient(from 180deg, var(--c), color-mix(in srgb, var(--c) 25%, transparent), var(--c));
  transition: box-shadow .25s, transform .25s;
}
.g-thumb img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  display: block;
  background: #11142A;
  border: 2px solid #05060D;
}
.g-name {
  max-width: 100%;
  font-size: 0.75rem;
  color: #9AA3C7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  direction: ltr;
}
@media (hover: hover) {
  .g-item:hover { transform: translateY(-4px); }
  .g-item:hover .g-thumb { box-shadow: 0 0 22px color-mix(in srgb, var(--c) 55%, transparent); }
  .g-item:hover .g-name { color: #E8ECF5; }
}
.g-item:focus-visible { outline: none; }
.g-item:focus-visible .g-thumb { box-shadow: 0 0 0 2px #fff, 0 0 22px var(--c); }

.g-item.active .g-thumb {
  transform: scale(1.12);
  box-shadow: 0 0 0 2px #fff, 0 0 28px var(--c), 0 0 60px color-mix(in srgb, var(--c) 40%, transparent);
  animation: pulse 2.4s ease-in-out infinite;
}
.g-item.active .g-name { color: #fff; font-weight: 700; }
.g-item.pending .g-thumb { animation: spin 0.9s linear infinite; }

@keyframes pulse {
  50% { box-shadow: 0 0 0 2px #fff, 0 0 14px var(--c), 0 0 34px color-mix(in srgb, var(--c) 30%, transparent); }
}
@keyframes spin {
  to { filter: hue-rotate(360deg) brightness(1.4); }
}

.g-arrow {
  position: absolute;
  top: 38%;
  z-index: 2;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(10, 12, 28, 0.85);
  color: #fff;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  backdrop-filter: blur(6px);
  transition: box-shadow .2s, opacity .2s;
}
.g-arrow:hover { box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 55%, transparent); }
.g-prev { right: -0.4rem; }
.g-next { left: -0.4rem; }
.g-empty { text-align: center; color: #9AA3C7; padding: 1.5rem 0; }

@media (max-width: 640px) {
  .g-arrow { display: none; }
  .g-search input { width: 7rem; }
  .g-item { width: 74px; }
  .g-thumb { width: 64px; height: 64px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""

_JS = """
const instances = new WeakMap()

function centerItem(strip, item, smooth) {
  const s = strip.getBoundingClientRect()
  const r = item.getBoundingClientRect()
  const delta = (r.left + r.width / 2) - (s.left + s.width / 2)
  strip.scrollBy({ left: delta, behavior: smooth ? "smooth" : "auto" })
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const root = parentElement.querySelector(".g")
  if (!root || !data) return
  const strip = root.querySelector(".g-strip")
  const input = root.querySelector(".g-search input")
  const empty = root.querySelector(".g-empty")
  root.style.setProperty("--accent", data.accent || "#FFE81F")

  let state = instances.get(parentElement)
  if (!state) {
    state = { built: false, selected: null }
    instances.set(parentElement, state)
  }

  // Build the thumbnails once; later runs only move the selection
  if (!state.built) {
    state.built = true
    const frag = document.createDocumentFragment()
    for (const item of data.items || []) {
      const btn = document.createElement("button")
      btn.type = "button"
      btn.className = "g-item"
      btn.setAttribute("role", "listitem")
      btn.dataset.id = String(item.id)
      btn.dataset.name = item.name.toLowerCase()
      btn.title = `${item.name} · ${item.side}`
      btn.style.setProperty("--c", item.color)
      const thumb = document.createElement("span")
      thumb.className = "g-thumb"
      const img = document.createElement("img")
      img.loading = "lazy"
      img.decoding = "async"
      img.alt = ""
      img.src = item.thumb
      thumb.append(img)
      const name = document.createElement("span")
      name.className = "g-name"
      name.textContent = item.name
      btn.append(thumb, name)
      frag.append(btn)
    }
    strip.append(frag)
    root.querySelector(".g-count").textContent = `· ${(data.items || []).length} דמויות`
  }

  const items = [...strip.querySelectorAll(".g-item")]
  const firstRun = state.selected === null
  if (state.selected !== data.selected) {
    state.selected = data.selected
    let active = null
    for (const el of items) {
      el.classList.remove("pending")
      const on = el.dataset.id === String(data.selected)
      el.classList.toggle("active", on)
      el.setAttribute("aria-current", on ? "true" : "false")
      if (on) active = el
    }
    if (active) requestAnimationFrame(() => centerItem(strip, active, !firstRun))
  }

  strip.onclick = (e) => {
    const btn = e.target.closest(".g-item")
    if (!btn || btn.classList.contains("active")) return
    btn.classList.add("pending")
    window.swSound?.play("select")
    setTriggerValue("selected", Number(btn.dataset.id))
  }

  root.querySelector(".g-random").onclick = () => {
    window.swSound?.play("saber")
    setTriggerValue("random", Date.now())
  }

  input.oninput = () => {
    const q = input.value.trim().toLowerCase()
    let shown = 0
    for (const el of items) {
      const match = !q || el.dataset.name.includes(q)
      el.hidden = !match
      if (match) shown++
    }
    empty.hidden = shown > 0
  }

  const page = () => strip.clientWidth * 0.8
  root.querySelector(".g-prev").onclick = () => strip.scrollBy({ left: page(), behavior: "smooth" })
  root.querySelector(".g-next").onclick = () => strip.scrollBy({ left: -page(), behavior: "smooth" })

  // Vertical mouse wheel scrolls the strip sideways
  strip.onwheel = (e) => {
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return
    const max = strip.scrollWidth - strip.clientWidth
    if (max <= 0) return
    e.preventDefault()
    strip.scrollBy({ left: -e.deltaY })
  }

  // Drag to scroll with the mouse (touch already scrolls natively)
  let drag = null
  strip.onpointerdown = (e) => {
    if (e.pointerType !== "mouse" || e.button !== 0) return
    drag = { x: e.clientX, left: strip.scrollLeft, moved: false }
  }
  strip.onpointermove = (e) => {
    if (!drag) return
    const dx = e.clientX - drag.x
    if (!drag.moved && Math.abs(dx) > 5) {
      drag.moved = true
      strip.classList.add("dragging")
      strip.setPointerCapture(e.pointerId)
    }
    if (drag.moved) strip.scrollLeft = drag.left - dx
  }
  strip.onpointerup = strip.onpointercancel = (e) => {
    if (drag && drag.moved) {
      strip.releasePointerCapture(e.pointerId)
      // Swallow the click that follows a drag
      strip.addEventListener("click", (ev) => ev.stopImmediatePropagation(), { capture: true, once: true })
    }
    drag = null
    strip.classList.remove("dragging")
  }
}
"""

_GALLERY = st.components.v2.component(
    "sw_character_gallery",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def character_gallery(
    *,
    items: list[dict],
    selected: int | None,
    accent: str,
    on_select: Callable[[], None],
    on_random: Callable[[], None],
    key: str = "character_gallery",
):
    """Render the gallery. Read the chosen id from st.session_state[key].selected inside `on_select`."""
    return _GALLERY(
        data={"items": items, "selected": selected, "accent": accent},
        key=key,
        on_selected_change=on_select,
        on_random_change=on_random,
    )
