/**
 * Animação do rosto — olhos, piscar (um/b dois), boca, humor.
 * Canvas-free: DOM + SVG path para boca (d morphing).
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

  const maxOffset = 28; // % do raio aproximado — movimento da íris/pupila

  let targetLX = 0,
    targetLY = 0,
    targetRX = 0,
    targetRY = 0;
  let curLX = 0,
    curLY = 0,
    curRX = 0,
    curRY = 0;

  function mouthDNeutral() {
    return "M 20 45 Q 100 75 180 45";
  }

  function mouthDSmile(amount) {
    // amount 0..1
    const dip = 35 + amount * 25;
    return `M 25 40 Q 100 ${dip} 175 40`;
  }

  function mouthDHappy() {
    return "M 15 35 Q 100 95 185 35";
  }

  function mouthDTalk(open) {
    const y = 50 + open * 18;
    return `M 35 ${y - 8} Q 100 ${y + 12} 165 ${y - 8}`;
  }

  function mouthInnerD(pathD) {
    if (!mouthInner) return;
    const closed = pathD.includes("Q 100 75");
    if (closed) {
      mouthInner.setAttribute("d", "M 25 42 Q 100 68 175 42 Z");
    } else {
      mouthInner.setAttribute("d", "");
    }
  }

  function setMouth(pathD) {
    mouthPath.setAttribute("d", pathD);
    mouthInnerD(pathD);
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
    setMouth(mouthDHappy());
    if (happyTimer) clearTimeout(happyTimer);
    happyTimer = setTimeout(() => {
      face.classList.remove("happy");
      setMouth(mouthDSmile(0.4));
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
      const open = (n % 2) * 0.7 + Math.random() * 0.3;
      if (!face.classList.contains("happy")) {
        setMouth(mouthDTalk(open));
      }
      if (n > 14) {
        clearInterval(talkInterval);
        talkInterval = null;
        face.classList.remove("talking");
        if (!face.classList.contains("happy")) {
          setMouth(mouthDSmile(0.35));
        }
      }
    }, 180);
  }

  function scheduleTalk() {
    setInterval(() => {
      if (Math.random() < 0.18 && !face.classList.contains("happy")) {
        burstTalk();
      }
    }, 12000);
  }

  randomEyeTargets();
  setMouth(mouthDSmile(0.35));
  tick();
  scheduleSaccade();
  scheduleBlink();
  scheduleMood();
  scheduleTalk();

  document.addEventListener("click", () => {
    enterHappy();
    burstTalk();
  });
})();
