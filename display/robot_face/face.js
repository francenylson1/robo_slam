/**
 * Animação do rosto — olhos, piscar (um/b dois), boca em arco (sorriso), fala.
 */
(function () {
  "use strict";

  const leftEye = document.getElementById("eye-left");
  const rightEye = document.getElementById("eye-right");
  const leftPupil = leftEye.querySelector(".pupil");
  const rightPupil = rightEye.querySelector(".pupil");
  const face = document.getElementById("face");
  const mouthPath = document.getElementById("mouth-path");
  const mouthInner = document.getElementById("mouth-inner");

  const maxOffset = 28;

  let targetLX = 0,
    targetLY = 0,
    targetRX = 0,
    targetRY = 0;
  let curLX = 0,
    curLY = 0,
    curRX = 0,
    curRY = 0;

  /** Arco de sorriso: cantos em y, vértice da curva em dip (maior = sorriso mais “aberto”). */
  function pathsSmile(cornerL, cornerR, y, dip) {
    const d = `M ${cornerL} ${y} Q 100 ${dip} ${cornerR} ${y}`;
    const inner = `M ${cornerL + 1} ${y + 0.5} Q 100 ${dip} ${cornerR - 1} ${y + 0.5} L ${cornerR - 1} ${y + 9} Q 100 ${dip + 8} ${cornerL + 1} ${y + 9} Z`;
    return { d, inner };
  }

  /** Baseline: sempre curvado (aspecto feliz), não linha reta. */
  function mouthDRest() {
    return pathsSmile(20, 180, 46, 78);
  }

  /** Momento extra feliz (clique / humor). */
  function mouthDHappy() {
    return pathsSmile(12, 188, 39, 96);
  }

  /**
   * Fala: curvatura maior que o repouso, depois volta ao rest com setMouth(mouthDRest).
   * intensity 0..1 — quanto mais alto, mais “sorriso” acentuado (boca mais animada).
   */
  function mouthDTalk(intensity) {
    const t = Math.min(1, Math.max(0, intensity));
    const dip = 78 + t * 24;
    const y = 46 - t * 5;
    const cornerL = 18 - t * 3;
    const cornerR = 182 + t * 3;
    return pathsSmile(cornerL, cornerR, y, dip);
  }

  function setMouthParts(parts) {
    mouthPath.setAttribute("d", parts.d);
    if (mouthInner) {
      mouthInner.setAttribute("d", parts.inner);
    }
  }

  function setPupilTransform(el, x, y) {
    el.style.transform = `translate(calc(-50% + ${x}%), calc(-50% + ${y}%))`;
  }

  function tick() {
    curLX += (targetLX - curLX) * 0.12;
    curLY += (targetLY - curLY) * 0.12;
    curRX += (targetRX - curRX) * 0.12;
    curRY += (targetRY - curRY) * 0.12;
    setPupilTransform(leftPupil, curLX, curLY);
    setPupilTransform(rightPupil, curRX, curRY);
    requestAnimationFrame(tick);
  }

  function randomEyeTargets() {
    const r = () => (Math.random() - 0.5) * 2 * maxOffset;
    targetLX = r();
    targetLY = r();
    targetRX = r();
    targetRY = r();
    if (Math.random() < 0.35) {
      targetRX = targetLX + (Math.random() - 0.5) * 12;
      targetRY = targetLY + (Math.random() - 0.5) * 12;
    }
  }

  function blinkEye(eyeEl, done) {
    eyeEl.classList.remove("open");
    eyeEl.classList.add("blinking");
    setTimeout(() => {
      eyeEl.classList.add("open");
    }, 150);
    setTimeout(() => {
      eyeEl.classList.remove("blinking", "open");
      if (done) done();
    }, 420);
  }

  function blinkBoth() {
    blinkEye(leftEye);
    blinkEye(rightEye);
  }

  function winkLeft() {
    blinkEye(leftEye);
  }

  function winkRight() {
    blinkEye(rightEye);
  }

  function scheduleBlink() {
    const delay = 2000 + Math.random() * 4500;
    setTimeout(() => {
      const r = Math.random();
      if (r < 0.55) blinkBoth();
      else if (r < 0.77) winkLeft();
      else winkRight();
      scheduleBlink();
    }, delay);
  }

  function scheduleSaccade() {
    setInterval(randomEyeTargets, 2200 + Math.random() * 2800);
  }

  let happyTimer = null;

  function enterHappy() {
    face.classList.add("happy");
    setMouthParts(mouthDHappy());
    if (happyTimer) clearTimeout(happyTimer);
    happyTimer = setTimeout(() => {
      face.classList.remove("happy");
      setMouthParts(mouthDRest());
    }, 4000 + Math.random() * 3000);
  }

  function scheduleMood() {
    setInterval(() => {
      if (face.classList.contains("happy")) return;
      if (Math.random() < 0.22) enterHappy();
    }, 8000);
  }

  let talkInterval = null;

  function burstTalk() {
    if (talkInterval) return;
    face.classList.add("talking");
    let n = 0;
    talkInterval = setInterval(() => {
      n++;
      const phase = n % 2 === 0 ? 0.35 : 0.92;
      const jitter = Math.random() * 0.08;
      if (!face.classList.contains("happy")) {
        setMouthParts(mouthDTalk(phase + jitter));
      }
      if (n > 14) {
        clearInterval(talkInterval);
        talkInterval = null;
        face.classList.remove("talking");
        if (!face.classList.contains("happy")) {
          setMouthParts(mouthDRest());
        }
      }
    }, 200);
  }

  function scheduleTalk() {
    setInterval(() => {
      if (Math.random() < 0.18 && !face.classList.contains("happy")) {
        burstTalk();
      }
    }, 12000);
  }

  randomEyeTargets();
  setMouthParts(mouthDRest());
  tick();
  scheduleSaccade();
  scheduleBlink();
  scheduleMood();
  scheduleTalk();

  document.addEventListener("click", () => {
    enterHappy();
    burstTalk();
  });

  function startTeleopFooterPoll() {
    const bar = document.getElementById("face-footer");
    if (!bar) {
      return;
    }
    async function poll() {
      try {
        const r = await fetch("/api/teleop_status", { cache: "no-store" });
        const j = await r.json();
        if (j.footer_active) {
          bar.textContent = "Estado: \"[A] Motores ARMADOS\"";
          bar.classList.add("visible");
        } else {
          bar.textContent = "";
          bar.classList.remove("visible");
        }
      } catch (_e) {
        /* file:// ou servidor inativo */
      }
    }
    poll();
    setInterval(poll, 200);
  }

  if (new URLSearchParams(location.search).get("teleop") === "1") {
    startTeleopFooterPoll();
  }
})();
