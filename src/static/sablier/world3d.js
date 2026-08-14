const TAU = Math.PI * 2;
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const smoothstep = (min, max, value) => {
  const t = clamp((value - min) / (max - min));
  return t * t * (3 - 2 * t);
};

function seeded(index, salt = 1) {
  const value = Math.sin(index * 91.733 + salt * 37.719) * 43758.5453;
  return Math.abs(value - Math.floor(value));
}

function duneHeight(x, z) {
  const longWave = Math.sin(x * 0.12 + z * 0.075) * 1.48;
  const crossing = Math.sin(x * 0.075 - z * 0.155 + 1.7) * 0.76;
  const crest = Math.pow(0.5 + 0.5 * Math.sin(x * 0.22 + z * 0.105 + 0.8), 3.2) * 1.42;
  const distantRise = (1 - smoothstep(-24, -1, z)) * 1.72;
  return longWave + crossing + crest + distantRise - 0.48;
}

function makeNoiseTexture(THREE, mobile) {
  const size = mobile ? 256 : 512;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d", { alpha: false });
  const pixels = context.createImageData(size, size);

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const u = x / size * TAU;
      const v = y / size * TAU;
      const broad = Math.sin(u * 2 + v) + Math.sin(v * 3 - u) * 0.65 + Math.sin((u + v) * 5) * 0.32;
      const ripple = Math.sin(u * 29 + Math.sin(v * 3) * 0.85) * 0.5;
      const grain = (seeded(x + y * size, 17) - 0.5) * 12;
      const value = Math.round(157 + broad * 5.5 + ripple * 3.2 + grain);
      pixels.data[index] = value + 13;
      pixels.data[index + 1] = value;
      pixels.data[index + 2] = Math.max(0, value - 19);
      pixels.data[index + 3] = 255;
    }
  }

  context.putImageData(pixels, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3.5, 5.5);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = mobile ? 2 : 8;
  return texture;
}

function makeDunes(THREE, mobile, texture) {
  const segmentsX = mobile ? 72 : 132;
  const segmentsZ = mobile ? 84 : 156;
  const geometry = new THREE.PlaneGeometry(54, 66, segmentsX, segmentsZ);
  const position = geometry.attributes.position;

  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const z = -position.getY(index);
    position.setZ(index, duneHeight(x, z));
  }

  geometry.computeVertexNormals();
  geometry.rotateX(-Math.PI / 2);
  const material = new THREE.MeshPhysicalMaterial({
    color: 0xd18a48,
    map: texture,
    bumpMap: texture,
    bumpScale: 0.085,
    roughness: 0.88,
    metalness: 0.015,
    clearcoat: 0.08,
    clearcoatRoughness: 0.72,
    envMapIntensity: 0.42,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.receiveShadow = true;
  return mesh;
}

function makeDuneRidge(THREE, material, mobile, spec) {
  const geometry = new THREE.PlaneGeometry(
    spec.width,
    spec.depth,
    mobile ? 42 : 76,
    mobile ? 18 : 32,
  );
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const z = -position.getY(index);
    const depthRatio = z / (spec.depth * 0.5);
    const envelope = Math.exp(-depthRatio * depthRatio * 2.35);
    const windCrest = 0.82 + Math.sin(x * 0.21 + spec.phase) * 0.18;
    const shoulder = Math.sin(x * 0.075 - z * 0.16 + spec.phase) * spec.height * 0.12;
    position.setZ(index, envelope * spec.height * windCrest + shoulder - spec.height * 0.34);
  }
  geometry.computeVertexNormals();
  geometry.rotateX(-Math.PI / 2);
  const ridge = new THREE.Mesh(geometry, material);
  ridge.position.set(spec.x, spec.y, spec.z);
  ridge.castShadow = !mobile;
  ridge.receiveShadow = true;
  return ridge;
}

function makeSky(THREE) {
  const uniforms = {
    topColor: { value: new THREE.Color(0x365d82) },
    horizonColor: { value: new THREE.Color(0xe4a061) },
    groundColor: { value: new THREE.Color(0x6f3f29) },
    sunDirection: { value: new THREE.Vector3(0.5, 0.45, -0.75).normalize() },
    sunColor: { value: new THREE.Color(0xffe4b0) },
    starVisibility: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms,
    vertexShader: `
      varying vec3 vWorldDirection;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        vWorldDirection = normalize(worldPosition.xyz - cameraPosition);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vWorldDirection;
      uniform vec3 topColor;
      uniform vec3 horizonColor;
      uniform vec3 groundColor;
      uniform vec3 sunDirection;
      uniform vec3 sunColor;
      uniform float starVisibility;

      float hash21(vec2 value) {
        value = fract(value * vec2(123.34, 456.21));
        value += dot(value, value + 45.32);
        return fract(value.x * value.y);
      }

      void main() {
        vec3 ray = normalize(vWorldDirection);
        float elevation = ray.y;
        float upper = smoothstep(-0.13, 0.24, elevation);
        float lower = smoothstep(-0.22, 0.04, elevation);
        vec3 color = mix(groundColor, horizonColor, lower);
        color = mix(color, topColor, upper);

        float sunDot = max(dot(ray, normalize(sunDirection)), 0.0);
        float sunDisk = pow(sunDot, 1800.0);
        float sunHalo = pow(sunDot, 38.0) * 0.28;
        color += sunColor * (sunDisk * 2.7 + sunHalo);

        vec2 starCell = floor((ray.xz / max(0.08, ray.y + 1.15)) * 410.0);
        float starSeed = hash21(starCell);
        float star = step(0.9962, starSeed) * pow(starSeed, 36.0);
        star *= smoothstep(-0.04, 0.28, elevation) * starVisibility;
        color += vec3(0.78, 0.86, 1.0) * star * 1.45;
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(76, 48, 30), material);
  mesh.frustumCulled = false;
  return { mesh, uniforms };
}

function materialSet(THREE) {
  return {
    stone: new THREE.MeshPhysicalMaterial({
      color: 0x6a5140,
      roughness: 0.91,
      metalness: 0.02,
      clearcoat: 0.06,
    }),
    darkStone: new THREE.MeshStandardMaterial({ color: 0x302922, roughness: 0.98 }),
    bronze: new THREE.MeshPhysicalMaterial({
      color: 0x5c3c26,
      metalness: 0.91,
      roughness: 0.28,
      clearcoat: 0.58,
      clearcoatRoughness: 0.16,
    }),
    glass: new THREE.MeshPhysicalMaterial({
      color: 0x8bc4ca,
      roughness: 0.12,
      transmission: 0.42,
      thickness: 0.72,
      ior: 1.47,
      transparent: true,
      opacity: 0.6,
      metalness: 0,
      clearcoat: 1,
      clearcoatRoughness: 0.05,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
    glow: new THREE.MeshStandardMaterial({
      color: 0x614126,
      emissive: 0xffa84c,
      emissiveIntensity: 0.08,
      roughness: 0.5,
      transparent: true,
      opacity: 0.5,
    }),
  };
}

function shadowed(mesh, mobile) {
  mesh.castShadow = !mobile;
  mesh.receiveShadow = true;
  return mesh;
}

function makeObservatory(THREE, mobile, materials) {
  const root = new THREE.Group();
  root.position.set(6.4, duneHeight(6.4, -13.2) - 0.55, -13.2);

  const base = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(3.2, 3.65, 1.05, 48),
    materials.stone,
  ), mobile);
  base.position.y = 0.28;
  root.add(base);

  const terrace = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.5, 4.9, 0.28, 64),
    materials.darkStone,
  ), mobile);
  terrace.position.y = -0.18;
  root.add(terrace);

  const dome = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(2.48, mobile ? 32 : 64, mobile ? 16 : 28, 0, TAU, 0, Math.PI / 2),
    materials.glass,
  ), mobile);
  dome.position.y = 0.82;
  root.add(dome);

  const innerGlow = new THREE.Mesh(
    new THREE.SphereGeometry(2.27, 32, 16, 0, TAU, 0, Math.PI / 2),
    materials.glow,
  );
  innerGlow.position.y = 0.8;
  innerGlow.scale.set(0.985, 0.985, 0.985);
  root.add(innerGlow);

  const crown = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(2.5, 0.095, 10, 80),
    materials.bronze,
  ), mobile);
  crown.rotation.x = Math.PI / 2;
  crown.position.y = 0.82;
  root.add(crown);

  for (let index = 0; index < 7; index += 1) {
    const rib = shadowed(new THREE.Mesh(
      new THREE.TorusGeometry(2.5, 0.042, 8, 56, Math.PI),
      materials.bronze,
    ), mobile);
    rib.rotation.y = index * Math.PI / 7;
    rib.position.y = 0.82;
    root.add(rib);
  }

  const meridian = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(4.45, 0.22, 12, 96, Math.PI * 1.58),
    materials.bronze,
  ), mobile);
  meridian.position.set(0, 3.18, 0.08);
  meridian.rotation.z = -0.29;
  root.add(meridian);

  const crossRing = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(3.74, 0.105, 9, 88, Math.PI * 1.7),
    materials.bronze,
  ), mobile);
  crossRing.position.set(0, 3.18, 0.08);
  crossRing.rotation.set(0.2, 0.88, 0.18);
  root.add(crossRing);

  const columns = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.18, 0.28, 2.9, 9),
    materials.stone,
    11,
  );
  const transform = new THREE.Object3D();
  for (let index = 0; index < 11; index += 1) {
    const angle = index / 11 * TAU;
    const broken = 0.62 + seeded(index, 33) * 0.43;
    transform.position.set(Math.cos(angle) * 4.0, 0.25 + broken, Math.sin(angle) * 4.0);
    transform.rotation.set((seeded(index, 35) - 0.5) * 0.08, -angle, (seeded(index, 37) - 0.5) * 0.07);
    transform.scale.set(1, broken, 1);
    transform.updateMatrix();
    columns.setMatrixAt(index, transform.matrix);
  }
  columns.castShadow = !mobile;
  columns.receiveShadow = true;
  root.add(columns);

  const beacon = new THREE.Mesh(
    new THREE.SphereGeometry(0.09, 16, 10),
    new THREE.MeshBasicMaterial({ color: 0xffd58f }),
  );
  beacon.position.set(-0.78, 1.16, 2.38);
  root.add(beacon);

  return { root, innerGlow, beacon };
}

function makeRuins(THREE, mobile, material) {
  const count = mobile ? 22 : 42;
  const geometry = new THREE.IcosahedronGeometry(0.72, 1);
  const rocks = new THREE.InstancedMesh(geometry, material, count);
  const transform = new THREE.Object3D();

  for (let index = 0; index < count; index += 1) {
    const side = index % 2 === 0 ? -1 : 1;
    const x = side * (4.2 + seeded(index, 101) * 18);
    const z = 9 - seeded(index, 103) * 39;
    const scale = 0.35 + Math.pow(seeded(index, 107), 2) * (z > 2 ? 2.4 : 1.35);
    transform.position.set(x, duneHeight(x, z) - 0.15 + scale * 0.25, z);
    transform.rotation.set(seeded(index, 109) * TAU, seeded(index, 113) * TAU, seeded(index, 127) * TAU);
    transform.scale.set(scale * (0.8 + seeded(index, 131)), scale, scale * (0.7 + seeded(index, 137) * 0.7));
    transform.updateMatrix();
    rocks.setMatrixAt(index, transform.matrix);
  }

  rocks.castShadow = !mobile;
  rocks.receiveShadow = true;
  return rocks;
}

function makeDust(THREE, mobile) {
  const count = mobile ? 420 : 980;
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);

  for (let index = 0; index < count; index += 1) {
    positions[index * 3] = (seeded(index, 151) - 0.5) * 44;
    positions[index * 3 + 1] = 0.12 + seeded(index, 157) * 5.2;
    positions[index * 3 + 2] = 12 - seeded(index, 163) * 46;
    sizes[index] = 0.7 + seeded(index, 167) * 2.1;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: { opacity: { value: 0.16 } },
    vertexShader: `
      attribute float size;
      varying float vFade;
      void main() {
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (52.0 / -mvPosition.z);
        vFade = 1.0 - smoothstep(5.0, 48.0, -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform float opacity;
      varying float vFade;
      void main() {
        vec2 point = gl_PointCoord - 0.5;
        float alpha = 1.0 - smoothstep(0.05, 0.5, length(point));
        gl_FragColor = vec4(0.95, 0.68, 0.38, alpha * opacity * vFade);
      }
    `,
  });
  return { points: new THREE.Points(geometry, material), count, material };
}

function makeHeatVeil(THREE) {
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      time: { value: 0 },
      strength: { value: 0.012 },
    },
    vertexShader: `
      uniform float time;
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vec3 transformed = position;
        transformed.x += sin(position.y * 8.0 + time * 0.8) * 0.07;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(transformed, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform float time;
      uniform float strength;
      void main() {
        float band = sin(vUv.y * 24.0 + time * 0.7 + sin(vUv.x * 9.0) * 1.4);
        float fade = smoothstep(0.0, 0.22, vUv.y) * (1.0 - smoothstep(0.55, 1.0, vUv.y));
        gl_FragColor = vec4(1.0, 0.76, 0.55, (0.5 + band * 0.5) * fade * strength);
      }
    `,
  });
  const veil = new THREE.Mesh(new THREE.PlaneGeometry(34, 5.2, 60, 18), material);
  veil.position.set(0, 2.5, -19);
  return { veil, material };
}

function createWorld(THREE, app, stage, canvas) {
  const mobile = matchMedia("(max-width: 760px)").matches;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fallbackCanvas = stage.querySelector("#decor-canvas");
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: !mobile,
    alpha: false,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.15 : 1.55));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  renderer.shadowMap.enabled = !mobile;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0xb87952, 0.0175);
  const camera = new THREE.PerspectiveCamera(mobile ? 44 : 38, 1, 0.1, 120);
  camera.position.set(0.2, mobile ? 3.25 : 3.55, mobile ? 13.8 : 15.6);

  const sky = makeSky(THREE);
  scene.add(sky.mesh);

  const sandTexture = makeNoiseTexture(THREE, mobile);
  const dunes = makeDunes(THREE, mobile, sandTexture);
  scene.add(dunes);
  const ridgeMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd99152,
    map: sandTexture,
    bumpMap: sandTexture,
    bumpScale: 0.045,
    roughness: 0.94,
    metalness: 0,
    clearcoat: 0.035,
  });
  scene.add(
    makeDuneRidge(THREE, ridgeMaterial, mobile, {
      x: -3.5, y: -0.25, z: -18, width: 58, depth: 17, height: 4.8, phase: 0.7,
    }),
    makeDuneRidge(THREE, ridgeMaterial, mobile, {
      x: -7, y: -0.65, z: -5.5, width: 48, depth: 16, height: 4.0, phase: 2.1,
    }),
    makeDuneRidge(THREE, ridgeMaterial, mobile, {
      x: 5, y: -0.9, z: 7.5, width: 54, depth: 18, height: 4.5, phase: 4.4,
    }),
  );

  const materials = materialSet(THREE);
  const observatory = makeObservatory(THREE, mobile, materials);
  scene.add(observatory.root);

  const dust = makeDust(THREE, mobile);
  dust.points.frustumCulled = false;
  scene.add(dust.points);

  const heat = makeHeatVeil(THREE);
  scene.add(heat.veil);

  const hemisphere = new THREE.HemisphereLight(0xa6c2dc, 0x492717, 1.7);
  const sun = new THREE.DirectionalLight(0xffd0a0, 4.2);
  sun.position.set(-16, 15, 7);
  sun.castShadow = !mobile;
  sun.shadow.mapSize.set(mobile ? 512 : 1536, mobile ? 512 : 1536);
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 65;
  sun.shadow.camera.left = -18;
  sun.shadow.camera.right = 18;
  sun.shadow.camera.top = 18;
  sun.shadow.camera.bottom = -18;
  sun.shadow.bias = -0.0003;

  const observatoryLight = new THREE.PointLight(0xffa751, 0, 18, 2);
  observatoryLight.position.set(6.4, observatory.root.position.y + 1.65, -11.3);
  scene.add(hemisphere, sun, observatoryLight);

  let width = 0;
  let height = 0;
  let frame = 0;
  let disposed = false;
  let visible = false;
  let firstFrame = false;
  let targetPointerX = 0;
  let targetPointerY = 0;
  let pointerX = 0;
  let pointerY = 0;
  let lastTime = 0;
  const target = new THREE.Vector3(0.4, 2.65, -11.8);
  const dayTop = new THREE.Color(0x315f88);
  const dayHorizon = new THREE.Color(0xd8a273);
  const dayGround = new THREE.Color(0x8c5737);
  const nightTop = new THREE.Color(0x030711);
  const nightHorizon = new THREE.Color(0x33253b);
  const nightGround = new THREE.Color(0x171018);
  const duskTop = new THREE.Color(0x293650);
  const duskHorizon = new THREE.Color(0xe0714e);
  const duskGround = new THREE.Color(0x5b2c2a);
  const warmSun = new THREE.Color(0xffb56f);
  const highSun = new THREE.Color(0xffedd2);

  function resize() {
    const rect = stage.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width));
    const nextHeight = Math.max(1, Math.round(rect.height));
    if (width === nextWidth && height === nextHeight) return;
    width = nextWidth;
    height = nextHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function temporalState() {
    const date = new Date();
    const hour = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
    const angle = (hour / 24 - 0.25) * TAU;
    const elevation = Math.sin(angle);
    const daylight = smoothstep(-0.1, 0.32, elevation);
    const twilight = smoothstep(-0.35, 0.08, elevation) * (1 - smoothstep(0.16, 0.58, elevation));
    const progressValue = Number.parseFloat(
      document.querySelector("#digital-progress")?.style.getPropertyValue("--progress") || "1",
    );
    const elapsed = 1 - (Number.isFinite(progressValue) ? clamp(progressValue) : 1);
    return { angle, elevation, daylight, twilight, elapsed };
  }

  function updateLight() {
    const temporal = temporalState();
    const darkness = 1 - temporal.daylight;
    const horizonMix = clamp(temporal.twilight * 0.92);
    sky.uniforms.topColor.value.copy(nightTop).lerp(dayTop, temporal.daylight).lerp(duskTop, horizonMix);
    sky.uniforms.horizonColor.value.copy(nightHorizon).lerp(dayHorizon, temporal.daylight).lerp(duskHorizon, horizonMix);
    sky.uniforms.groundColor.value.copy(nightGround).lerp(dayGround, temporal.daylight).lerp(duskGround, horizonMix);

    const sunDirection = sky.uniforms.sunDirection.value;
    sunDirection.set(Math.cos(temporal.angle) * 0.72, temporal.elevation, -0.72).normalize();
    sky.uniforms.sunColor.value.copy(warmSun).lerp(highSun, smoothstep(0.15, 0.75, temporal.elevation));
    sky.uniforms.starVisibility.value = clamp(darkness * 1.22 + temporal.elapsed * darkness * 0.15);

    sun.position.set(Math.cos(temporal.angle) * 25, Math.max(-2, temporal.elevation * 24), 8);
    sun.color.copy(warmSun).lerp(highSun, smoothstep(0.12, 0.72, temporal.elevation));
    sun.intensity = 0.06 + temporal.daylight * 4.5;
    hemisphere.intensity = 0.16 + temporal.daylight * 1.6;
    hemisphere.color.copy(nightTop).lerp(dayTop, temporal.daylight);
    scene.fog.color.copy(nightHorizon).lerp(dayHorizon, temporal.daylight).lerp(duskHorizon, horizonMix * 0.64);
    scene.fog.density = 0.0095 + temporal.twilight * 0.004 + darkness * 0.006;

    const artificial = smoothstep(0.18, 0.82, darkness);
    observatoryLight.intensity = artificial * 18;
    materials.glow.emissiveIntensity = 0.08 + artificial * 3.8;
    observatory.beacon.material.color.copy(warmSun).lerp(highSun, artificial);
    heat.material.uniforms.strength.value = reducedMotion ? 0 : temporal.daylight * 0.012;
    renderer.toneMappingExposure = 0.86 + temporal.daylight * 0.22;
  }

  function updateDensity() {
    const density = clamp(Number(app.dataset.decorDensity || 2), 0, 3);
    const ratio = [0, 0.24, 0.62, 1][density];
    dust.points.geometry.setDrawRange(0, Math.round(dust.count * ratio));
    dust.material.uniforms.opacity.value = 0.045 + ratio * 0.075;
    heat.veil.visible = density > 0 && !reducedMotion;
  }

  function render(time) {
    if (disposed) return;
    if (!visible || document.hidden) {
      frame = requestAnimationFrame(render);
      return;
    }
    if (time - lastTime < (mobile ? 28 : 14)) {
      frame = requestAnimationFrame(render);
      return;
    }
    const delta = Math.min(0.04, (time - lastTime) / 1000 || 0.016);
    lastTime = time;
    resize();
    updateLight();
    updateDensity();

    if (!reducedMotion) {
      pointerX += (targetPointerX - pointerX) * Math.min(1, delta * 2.2);
      pointerY += (targetPointerY - pointerY) * Math.min(1, delta * 2.2);
      camera.position.x = 0.2 + pointerX * 0.66 + Math.sin(time * 0.000075) * 0.18;
      camera.position.y = (mobile ? 3.25 : 3.55) - pointerY * 0.25 + Math.sin(time * 0.000052) * 0.08;
      dust.points.position.x = ((time * 0.00023) % 3.4) - 1.7;
      dust.points.rotation.y = Math.sin(time * 0.00008) * 0.012;
      heat.material.uniforms.time.value = time / 1000;
      observatory.root.rotation.y = Math.sin(time * 0.000035) * 0.008;
    }
    camera.lookAt(target);
    renderer.render(scene, camera);

    if (!firstFrame) {
      firstFrame = true;
      app.dataset.world3d = "ready";
    }
    frame = requestAnimationFrame(render);
  }

  function syncVisibility() {
    visible = app.dataset.ambience === "sahara";
    canvas.hidden = !visible;
    app.dataset.world3dActive = String(visible);
    if (fallbackCanvas) fallbackCanvas.style.opacity = visible ? "0" : "";
    if (visible) {
      width = 0;
      lastTime = 0;
    }
  }

  const mutationObserver = new MutationObserver(syncVisibility);
  mutationObserver.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
  const resizeObserver = new ResizeObserver(() => { width = 0; });
  resizeObserver.observe(stage);
  const pointerMove = (event) => {
    const rect = stage.getBoundingClientRect();
    targetPointerX = clamp((event.clientX - rect.left) / rect.width, 0, 1) * 2 - 1;
    targetPointerY = clamp((event.clientY - rect.top) / rect.height, 0, 1) * 2 - 1;
  };
  stage.addEventListener("pointermove", pointerMove, { passive: true });
  stage.addEventListener("pointerleave", () => { targetPointerX = 0; targetPointerY = 0; }, { passive: true });

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    visible = false;
    canvas.hidden = true;
    if (fallbackCanvas) fallbackCanvas.style.opacity = "";
    app.dataset.world3d = "fallback";
    app.dataset.world3dReason = "context-lost";
  }, { once: true });

  window.addEventListener("pagehide", () => {
    disposed = true;
    cancelAnimationFrame(frame);
    mutationObserver.disconnect();
    resizeObserver.disconnect();
    stage.removeEventListener("pointermove", pointerMove);
    scene.traverse((node) => {
      node.geometry?.dispose?.();
      const nodeMaterials = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
      for (const material of nodeMaterials) material.dispose?.();
    });
    sandTexture.dispose();
    renderer.dispose();
  }, { once: true });

  syncVisibility();
  frame = requestAnimationFrame(render);
}

async function boot() {
  const app = document.querySelector("#focus-app");
  const stage = document.querySelector("#focus-stage");
  const fallback = document.querySelector("#decor-canvas");
  if (!app || !stage || !fallback) return;

  // Sahara est volumineux. Ne pas construire ses dunes, textures et son deuxième
  // contexte WebGL tant que l'utilisateur se trouve dans un autre univers.
  let started = false;
  let observer;
  const start = async () => {
    if (started) return;
    started = true;
    observer?.disconnect();
    const canvas = document.createElement("canvas");
    canvas.className = "world-3d-canvas";
    canvas.setAttribute("aria-hidden", "true");
    canvas.hidden = true;
    stage.insertBefore(canvas, fallback);

    try {
      const THREE = await import(new URL("../vendor/three.module.js", import.meta.url).href);
      createWorld(THREE, app, stage, canvas);
    } catch (error) {
      canvas.remove();
      app.dataset.world3d = "fallback";
      app.dataset.world3dReason = "world-module-load";
      throw error;
    }
  };
  const maybeStart = () => {
    if (app.dataset.ambience === "sahara") {
      start().catch((error) => console.error("Univers Sahara 3D indisponible", error));
    }
  };

  if (app.dataset.ambience === "sahara") {
    await start();
  } else {
    observer = new MutationObserver(maybeStart);
    observer.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
    window.addEventListener("pagehide", () => observer?.disconnect(), { once: true });
  }
}

boot().catch((error) => console.error("Univers Sahara 3D indisponible", error));
