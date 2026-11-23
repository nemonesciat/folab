// ---------- View > Night: the view at night, to judge lights (nightlights.py) ----------
// The sun and sky down to a moonlit blue, the game's lights doing the lighting (W.pool: the nearest twelve), what glows
// (a shape with a glow picture: world.js material) lit up, and FOLab's night pieces as the game switches them: the lit
// ones at night, their day twins (editor IDs ending Day) by day. Only what you see; nothing in the mod changes.
const NV = {was: null};
const NV_DAY_GLOW = 0.35, NV_NIGHT_GLOW = 1.5;

const _nvDraw = vtDraw;
vtDraw = () => {
  _nvDraw();
  const box = $('#tab-view'); if (!box) return;
  const row = [...box.querySelectorAll('.vt-row')].find(r => r.querySelector('[data-v="sky"]'));
  const html = `<label class="vt-row" title="Moonlight, the game's lights and what glows; FOLab's night pieces as at night"><input type="checkbox" data-v="night" ${VT.night ? 'checked' : ''}> Night</label>`;
  if (row) row.insertAdjacentHTML('afterend', html); else box.insertAdjacentHTML('beforeend', html);
};

const _nvAssign = assignLights;
assignLights = () => {
  _nvAssign();
  if (!VT.night) return;
  W.hemi.intensity = 0.16; W.sun.intensity = 0.06; W.lamp.intensity = 0;
  for (const l of W.pool) if (l.intensity){ l.intensity = 2.6; l.distance *= 1.3; l.decay = 1.0; }
};

function nvTwin(base){
  if (!base || base.indexOf('FOLabNight') !== 0 || base === 'FOLabNightGenerator') return 0;
  return /Day$/.test(base) ? -1 : 1;           // (-1 a day twin, 1 a lit piece)
}

function nvFrame(){
  requestAnimationFrame(nvFrame);
  if (!W.scene) return;
  const night = !!VT.night;
  for (const g of W.group ? W.group.children : []){
    const t = g.userData.thing, k = t && nvTwin(t.base);
    if (!k) continue;
    const off = night ? k < 0 : k > 0;
    if (off && g.visible){ g.visible = false; g.userData.nvHid = true; }
    else if (!off && g.userData.nvHid){ g.visible = true; g.userData.nvHid = false; }
  }
  const skyNow = typeof SKYD !== 'undefined' ? SKYD.mesh : null;
  if (skyNow) skyNow.visible = !night;          // (its clouds are a sunny day's: at night the dark background instead)
  if (night && W.scene.background && W.scene.background.isColor && W.scene.background.getHex() !== 0x0b1020){
    if (NV.day) NV.day.bg = W.scene.background.clone();     // (going outside sets its own: kept for the day)
    W.scene.background.set(0x0b1020);
  }
  if (night && skyNow && NV.sky !== skyNow){ NV.sky = skyNow; skyNow.material.uniforms.haze.value.set(0x141c30); skyNow.material.uniforms.top.value.set(0x03050c); }
  if (night && W.scene.fog && W.scene.fog.color.getHex() !== 0x0b1020){
    // (the far hills are drawn unlit: at night they go into the dark sooner)
    NV.fog = NV.fog || {near: W.scene.fog.near, far: W.scene.fog.far};
    W.scene.fog.color.set(0x0b1020); W.scene.fog.near = 3000; W.scene.fog.far = 30000;
  }
  if (!night && NV.fog && W.scene.fog){ W.scene.fog.near = NV.fog.near; W.scene.fog.far = NV.fog.far; NV.fog = null; }
  if (NV.was === night) return;
  NV.was = night;
  W.glowLevel = night ? NV_NIGHT_GLOW : NV_DAY_GLOW;
  for (const m of W.glowMats || []) m.emissiveIntensity = W.glowLevel;
  const sky = typeof SKYD !== 'undefined' && SKYD.mesh ? SKYD.mesh.material.uniforms : null;
  if (night){
    NV.day = {bg: W.scene.background && W.scene.background.clone(), fog: W.scene.fog && W.scene.fog.color.clone(),
              haze: sky && sky.haze.value.clone(), top: sky && sky.top.value.clone()};
    if (W.scene.background && W.scene.background.isColor) W.scene.background.set(0x0b1020);
    if (W.scene.fog) W.scene.fog.color.set(0x0b1020);
    if (sky){ sky.haze.value.set(0x141c30); sky.top.value.set(0x03050c); }
  } else if (NV.day){
    if (NV.day.bg && W.scene.background && W.scene.background.isColor) W.scene.background.copy(NV.day.bg);
    if (NV.day.fog && W.scene.fog) W.scene.fog.color.copy(NV.day.fog);
    if (sky && NV.day.haze){ sky.haze.value.copy(NV.day.haze); sky.top.value.copy(NV.day.top); }
  }
  assignLights();
}
requestAnimationFrame(nvFrame);
