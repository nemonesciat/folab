// ---------- A sky, outside ----------
// A dome round the camera in place of the flat haze colour: the haze at the horizon (so the far hills still fade into
// it), blue overhead, a sun and thin cloud. Drawn behind everything, written to no depth. View > Sky turns it off; it is
// only a picture of a clear Mojave day, not the game's weather for the place.
const SKYD = {mesh: null};
const SKY_VERT = `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const SKY_FRAG = `
varying vec3 vDir;
uniform vec3 haze; uniform vec3 top; uniform vec3 sun;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int k = 0; k < 5; k++){ v += a * noise(p); p *= 2.03; a *= 0.5; } return v; }
void main(){
  vec3 d = normalize(vDir);
  float h = clamp(d.z, 0.0, 1.0);
  vec3 col = mix(haze, top, pow(h, 0.5));
  if (d.z < 0.0) col = haze * (1.0 + d.z * 0.35);                 // (under the horizon: the haze, a little darker)
  float s = max(dot(d, sun), 0.0);
  col += vec3(1.0, 0.9, 0.7) * (pow(s, 900.0) * 1.2 + pow(s, 12.0) * 0.14);
  if (d.z > 0.02){
    float c = smoothstep(0.52, 0.82, fbm(d.xy / (d.z + 0.18) * 1.3 + 7.0));
    col = mix(col, vec3(0.97, 0.95, 0.92), c * 0.55 * smoothstep(0.02, 0.22, d.z));
  }
  gl_FragColor = vec4(col, 1.0);
}`;

function skyMake(){
  const mat = new T.ShaderMaterial({vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, side: T.BackSide, depthWrite: false, depthTest: false, fog: false,
    uniforms: {haze: {value: new T.Color(SKY)}, top: {value: new T.Color(0x5f8fc4)}, sun: {value: new T.Vector3(-0.45, -0.35, 0.82).normalize()}}});
  const m = new T.Mesh(new T.SphereGeometry(1000, 32, 20), mat);
  m.renderOrder = -10; m.frustumCulled = false; m.userData.far = true;
  return m;
}
// (each frame: the dome goes where the camera is, so it is never nearer or further)
function skyFrame(){
  requestAnimationFrame(skyFrame);
  const want = !!(OUT.world && VT.sky !== false && W.scene && W.cam);
  if (!want){ if (SKYD.mesh && SKYD.mesh.parent){ SKYD.mesh.parent.remove(SKYD.mesh); } return; }
  if (!SKYD.mesh) SKYD.mesh = skyMake();
  if (SKYD.mesh.parent !== W.scene) W.scene.add(SKYD.mesh);
  SKYD.mesh.position.copy(W.cam.position);
}
requestAnimationFrame(skyFrame);
