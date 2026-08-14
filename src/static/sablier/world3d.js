const TAU = Math.PI * 2;
const WORLD_KEYS = new Set([
  "arbre_etoiles", "fontaine", "eden", "fleuve_temps", "souvenirs", "interstellaire",
  "galaxie", "heaven", "oasis", "abysses", "refuge_pluie", "aurores", "printemps",
  "ete", "automne", "hiver", "pluie", "ocean", "sahara", "foret", "orage",
  "braises", "aurore", "nuit",
]);
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const smoothstep = (min, max, value) => {
  const t = clamp((value - min) / Math.max(0.0001, max - min));
  return t * t * (3 - 2 * t);
};

function seeded(index, salt = 1) {
  const value = Math.sin(index * 91.733 + salt * 37.719) * 43758.5453;
  return Math.abs(value - Math.floor(value));
}

function sessionState(app) {
  const progressValue = Number.parseFloat(
    document.querySelector("#digital-progress")?.style.getPropertyValue("--progress") || "1",
  );
  const progress = Number.isFinite(progressValue) ? clamp(progressValue) : 1;
  const date = new Date();
  const hour = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
  const solarAngle = (hour / 24 - 0.25) * TAU;
  const solarElevation = Math.sin(solarAngle);
  const daylight = smoothstep(-0.14, 0.34, solarElevation);
  return {
    progress,
    elapsed: 1 - progress,
    daylight,
    solarAngle,
    solarElevation,
    density: clamp(Number(app.dataset.decorDensity || 2), 0, 3),
  };
}

function makeSurfaceTexture(THREE, palette, preset, mobile) {
  const size = mobile ? 192 : 320;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d", { alpha: false });
  const image = context.createImageData(size, size);
  const warmth = preset === "wood" || preset === "sand" || preset === "bark";
  const neutral = preset === "snow" ? 0.96 : 0.82;

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const broad = Math.sin(x * 0.071 + y * 0.037) + Math.sin(y * 0.113 - x * 0.029) * 0.62;
      const fine = (seeded(x + y * size, 19) - 0.5) * 2;
      let pattern = broad * 0.5 + fine * 0.55;
      if (preset === "wood") pattern += Math.sin(x * 0.22 + Math.sin(y * 0.035) * 2.4) * 1.1;
      if (preset === "sand") pattern += Math.sin(x * 0.85 + y * 0.11) * 0.32;
      if (preset === "bark") pattern += Math.abs(Math.sin(x * 0.14 + Math.sin(y * 0.06))) * 1.3;
      if (preset === "snow") pattern = broad * 0.25 + fine * 0.22;
      const lift = neutral * (1 + pattern * (preset === "snow" ? 0.045 : 0.105));
      image.data[index] = clamp(Math.round(255 * lift * (warmth ? 1.03 : 1)), 0, 255);
      image.data[index + 1] = clamp(Math.round(255 * lift), 0, 255);
      image.data[index + 2] = clamp(Math.round(255 * lift * (warmth ? 0.94 : 1.01)), 0, 255);
      image.data[index + 3] = 255;
    }
  }

  context.putImageData(image, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(preset === "wood" ? 5 : 7, preset === "wood" ? 2 : 7);
  texture.anisotropy = mobile ? 2 : 8;
  return texture;
}

function makeContactTexture(THREE) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(128, 64, 3, 128, 64, 116);
  gradient.addColorStop(0, "rgba(0,0,0,.72)");
  gradient.addColorStop(0.3, "rgba(0,0,0,.4)");
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 256, 128);
  return new THREE.CanvasTexture(canvas);
}

function makeSky(THREE, colors) {
  const uniforms = {
    topColor: { value: new THREE.Color(colors.top) },
    horizonColor: { value: new THREE.Color(colors.horizon) },
    groundColor: { value: new THREE.Color(colors.ground) },
    lightDirection: { value: new THREE.Vector3(-0.45, 0.36, 0.7).normalize() },
    lightColor: { value: new THREE.Color(colors.light) },
    starStrength: { value: colors.stars || 0 },
  };
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms,
    vertexShader: `
      varying vec3 vDirection;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        vDirection = normalize(worldPosition.xyz - cameraPosition);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vDirection;
      uniform vec3 topColor;
      uniform vec3 horizonColor;
      uniform vec3 groundColor;
      uniform vec3 lightDirection;
      uniform vec3 lightColor;
      uniform float starStrength;

      float hash21(vec2 value) {
        value = fract(value * vec2(123.34, 456.21));
        value += dot(value, value + 45.32);
        return fract(value.x * value.y);
      }

      void main() {
        vec3 ray = normalize(vDirection);
        float upper = smoothstep(-0.08, 0.32, ray.y);
        float lower = smoothstep(-0.24, 0.02, ray.y);
        vec3 color = mix(groundColor, horizonColor, lower);
        color = mix(color, topColor, upper);
        float towardLight = max(dot(ray, normalize(lightDirection)), 0.0);
        color += lightColor * pow(towardLight, 34.0) * 0.24;
        color += lightColor * pow(towardLight, 900.0) * 2.1;
        vec2 cell = floor((ray.xz / max(0.09, ray.y + 1.15)) * 430.0);
        float seed = hash21(cell);
        float star = step(0.9965, seed) * pow(seed, 28.0);
        star *= smoothstep(0.0, 0.24, ray.y) * starStrength;
        color += vec3(0.8, 0.9, 1.0) * star;
        gl_FragColor = vec4(color, 1.0);
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(90, 48, 32), material);
  mesh.frustumCulled = false;
  return { mesh, uniforms };
}

function configureShadow(light, mobile) {
  light.castShadow = true;
  light.shadow.mapSize.set(mobile ? 512 : 1536, mobile ? 512 : 1536);
  light.shadow.camera.near = 0.5;
  light.shadow.camera.far = 90;
  light.shadow.camera.left = -24;
  light.shadow.camera.right = 24;
  light.shadow.camera.top = 24;
  light.shadow.camera.bottom = -24;
  light.shadow.bias = -0.00035;
}

function shadowed(mesh, cast = true) {
  mesh.castShadow = cast;
  mesh.receiveShadow = true;
  return mesh;
}

function cylinderBetween(THREE, start, end, radius, material, radialSegments = 10) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.72, radius, length, radialSegments), material);
  mesh.position.copy(start).add(end).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  return shadowed(mesh);
}

function addContactShadow(THREE, pack, position, scale = [5.4, 2.7], opacity = 0.5) {
  const texture = makeContactTexture(THREE);
  pack.textures.push(texture);
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity,
    depthWrite: false,
    color: 0x111111,
  });
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(scale[0], scale[1]), material);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.copy(position);
  shadow.position.y += 0.018;
  shadow.renderOrder = 3;
  pack.scene.add(shadow);
  return shadow;
}

function makeParticles(THREE, count, bounds, color, size, opacity, salt = 1) {
  const positions = new Float32Array(count * 3);
  for (let index = 0; index < count; index += 1) {
    positions[index * 3] = bounds.x[0] + seeded(index, salt) * (bounds.x[1] - bounds.x[0]);
    positions[index * 3 + 1] = bounds.y[0] + seeded(index, salt + 7) * (bounds.y[1] - bounds.y[0]);
    positions[index * 3 + 2] = bounds.z[0] + seeded(index, salt + 13) * (bounds.z[1] - bounds.z[0]);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color,
    size,
    transparent: true,
    opacity,
    depthWrite: false,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return { points, material, count, baseOpacity: opacity };
}

function makeStudioEnvironment(THREE, renderer) {
  const environment = new THREE.Scene();
  const room = new THREE.Mesh(
    new THREE.BoxGeometry(30, 30, 30),
    new THREE.MeshBasicMaterial({ color: 0x18202a, side: THREE.BackSide }),
  );
  environment.add(room);
  const panels = [
    [-7, 6, -4, 0xffead0, 8, 4],
    [8, 1, 2, 0x91b7d4, 5, 8],
    [0, -6, -2, 0x5a6570, 12, 3],
  ];
  for (const [x, y, z, color, width, height] of panels) {
    const panel = new THREE.Mesh(
      new THREE.PlaneGeometry(width, height),
      new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide }),
    );
    panel.position.set(x, y, z);
    panel.lookAt(0, 0, 0);
    environment.add(panel);
  }
  const pmrem = new THREE.PMREMGenerator(renderer);
  const target = pmrem.fromScene(environment, 0.06);
  pmrem.dispose();
  environment.traverse((node) => {
    node.geometry?.dispose?.();
    node.material?.dispose?.();
  });
  return target;
}

function createPack(THREE, key, palette, mobile, environmentTexture) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(palette.fog, palette.fogDensity);
  scene.environment = environmentTexture;
  scene.environmentIntensity = 0.52;
  const camera = new THREE.PerspectiveCamera(mobile ? 47 : 39, 1, 0.1, 130);
  camera.position.set(0, mobile ? 4.1 : 4.6, mobile ? 14.8 : 16.4);
  const target = new THREE.Vector3(0, 1.3, -7.8);
  const sky = makeSky(THREE, palette.sky);
  scene.add(sky.mesh);
  const hemisphere = new THREE.HemisphereLight(palette.sky.top, palette.groundLight, palette.hemisphere || 1.35);
  const keyLight = new THREE.DirectionalLight(palette.sky.light, palette.keyIntensity || 3.2);
  keyLight.position.set(-13, 17, 8);
  configureShadow(keyLight, mobile);
  scene.add(hemisphere, keyLight);
  return {
    key,
    scene,
    camera,
    target,
    sky,
    hemisphere,
    keyLight,
    textures: [],
    particles: [],
    update: () => {},
  };
}

function buildStarTree(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "arbre_etoiles", {
    fog: 0x061824,
    fogDensity: 0.014,
    groundLight: 0x020406,
    hemisphere: 0.72,
    keyIntensity: 2.4,
    sky: { top: 0x01040b, horizon: 0x0c3246, ground: 0x031018, light: 0xffdfa0, stars: 1 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  const stoneTexture = makeSurfaceTexture(THREE, 0x253238, "stone", mobile);
  const barkTexture = makeSurfaceTexture(THREE, 0x3a2416, "bark", mobile);
  pack.textures.push(stoneTexture, barkTexture);

  const water = new THREE.Mesh(
    new THREE.PlaneGeometry(70, 80, 1, 1),
    new THREE.MeshPhysicalMaterial({
      color: 0x071a22,
      roughness: 0.18,
      metalness: 0.2,
      clearcoat: 1,
      clearcoatRoughness: 0.13,
      envMapIntensity: 0.75,
    }),
  );
  water.rotation.x = -Math.PI / 2;
  water.position.set(0, -1.42, -17);
  water.receiveShadow = true;
  scene.add(water);

  const island = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(6.6, 8.6, 1.7, 48),
    new THREE.MeshStandardMaterial({ color: 0x18261f, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.22, roughness: 0.97 }),
  ));
  island.scale.z = 0.82;
  island.position.set(2.2, -1.2, -11.8);
  scene.add(island);

  const focusSlab = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.7, 5.1, 0.52, 48),
    new THREE.MeshPhysicalMaterial({ color: 0x30383a, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.12, roughness: 0.84, clearcoat: 0.12 }),
  ));
  focusSlab.scale.z = 0.74;
  focusSlab.position.set(0, -0.72, -3.4);
  scene.add(focusSlab);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.44, -3.2), [5.7, 2.5], 0.48);

  const bark = new THREE.MeshStandardMaterial({ color: 0x342417, map: barkTexture, bumpMap: barkTexture, bumpScale: 0.18, roughness: 0.95 });
  const treeBase = new THREE.Vector3(3.6, -0.25, -11.7);
  const trunkTop = new THREE.Vector3(3.9, 7.2, -11.5);
  scene.add(cylinderBetween(THREE, treeBase, trunkTop, 0.78, bark, 14));
  for (let index = 0; index < 18; index += 1) {
    const side = index % 2 ? 1 : -1;
    const start = new THREE.Vector3(
      3.75 + (seeded(index, 21) - 0.5) * 0.35,
      2.1 + seeded(index, 23) * 4.6,
      -11.6 + (seeded(index, 25) - 0.5) * 0.3,
    );
    const end = new THREE.Vector3(
      3.8 + side * (1.4 + seeded(index, 27) * 2.8),
      start.y + 0.8 + seeded(index, 29) * 1.9,
      -11.5 + (seeded(index, 31) - 0.5) * 4.1,
    );
    scene.add(cylinderBetween(THREE, start, end, 0.17 + seeded(index, 33) * 0.14, bark, 8));
  }

  const leafMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x284431,
    roughness: 0.91,
    metalness: 0.02,
    emissive: 0x243718,
    emissiveIntensity: 0.07,
  });
  const leaves = new THREE.InstancedMesh(new THREE.SphereGeometry(0.44, mobile ? 9 : 12, mobile ? 7 : 9), leafMaterial, mobile ? 110 : 210);
  const transform = new THREE.Object3D();
  for (let index = 0; index < leaves.count; index += 1) {
    const angle = seeded(index, 41) * TAU;
    const radius = Math.sqrt(seeded(index, 43));
    transform.position.set(
      3.8 + Math.cos(angle) * radius * 4.15,
      5.45 + (seeded(index, 47) - 0.5) * 3.7,
      -11.5 + Math.sin(angle) * radius * 3.35,
    );
    const scale = 0.5 + seeded(index, 53) * 0.95;
    transform.scale.set(scale * (1.05+seeded(index,55)*.42),scale*(.72+seeded(index,56)*.42),scale);
    transform.rotation.set(seeded(index, 57) * TAU, seeded(index, 59) * TAU, seeded(index, 61) * TAU);
    transform.updateMatrix();
    leaves.setMatrixAt(index, transform.matrix);
  }
  leaves.castShadow = true;
  leaves.receiveShadow = true;
  scene.add(leaves);

  const canopyLight = new THREE.PointLight(0xffd58a, 3.2, 20, 2);
  canopyLight.position.set(3.6, 5.6, -10.3);
  scene.add(canopyLight);
  const stars = makeParticles(THREE, mobile ? 180 : 420, { x: [-28, 28], y: [4, 24], z: [-48, -8] }, 0xdaf4ff, 0.055, 0.58, 71);
  scene.add(stars.points);
  pack.particles.push(stars);

  const nightTop = new THREE.Color(0x01030a);
  const lateTop = new THREE.Color(0x020916);
  pack.update = (time, state, motion) => {
    pack.sky.uniforms.topColor.value.copy(nightTop).lerp(lateTop, state.elapsed * 0.58);
    pack.sky.uniforms.starStrength.value = 0.75 + state.elapsed * 0.25;
    leafMaterial.emissiveIntensity = 0.06 + state.elapsed * 0.2;
    canopyLight.intensity = 2.8 + state.elapsed * 4.2;
    water.material.roughness = 0.18 + Math.sin(time * 0.18) * 0.012 * motion;
    stars.points.rotation.y = time * 0.0012 * motion;
    stars.points.position.y = Math.sin(time * 0.12) * 0.08 * motion;
  };
  return pack;
}

function makeRainMaterial(THREE) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      time: { value: 0 },
      strength: { value: 0.7 },
    },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader: `
      varying vec2 vUv;
      uniform float time;
      uniform float strength;
      float hash21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
      void main(){
        vec2 grid=vec2(42.0,19.0);
        vec2 cell=floor(vUv*grid);
        float seed=hash21(cell);
        float speed=0.18+seed*0.38;
        float y=fract(vUv.y*grid.y+time*speed+seed*7.0);
        float x=fract(vUv.x*grid.x+seed)-0.5;
        float streak=smoothstep(0.075,0.0,abs(x))*smoothstep(0.9,0.2,y)*smoothstep(0.0,0.12,y);
        float bead=smoothstep(0.12,0.0,length(vec2(x,y-0.16))*vec2(1.0,2.7));
        float alpha=(streak*0.34+bead*0.62)*strength*(0.28+seed*0.72);
        gl_FragColor=vec4(vec3(0.66,0.82,0.9),alpha);
      }
    `,
  });
}

function buildRainRefuge(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "refuge_pluie", {
    fog: 0x101820,
    fogDensity: 0.012,
    groundLight: 0x120b07,
    hemisphere: 0.55,
    keyIntensity: 0.7,
    sky: { top: 0x0b1219, horizon: 0x273b49, ground: 0x0b0c0d, light: 0x91a9b7, stars: 0 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.6 : 4.0, mobile ? 14.2 : 15.8);
  pack.target.set(0, 1.5, -7.5);
  scene.fog.density = 0.008;
  const woodTexture = makeSurfaceTexture(THREE, 0x4b2e1c, "wood", mobile);
  const wallTexture = makeSurfaceTexture(THREE, 0x242526, "stone", mobile);
  pack.textures.push(woodTexture, wallTexture);

  const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x262729, map: wallTexture, bumpMap: wallTexture, bumpScale: 0.08, roughness: 0.94 });
  for (const [x, y, width, height] of [
    [-10.4, 5.1, 3.0, 17], [11.35, 5.1, 1.9, 17],
    [0.8, 12.0, 19, 3.2], [0.8, -1.3, 19, 2.6],
  ]) {
    const wallSection = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.45), wallMaterial), false);
    wallSection.position.set(x, y, -13.2);
    scene.add(wallSection);
  }
  const sideWall = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.6, 17, 28), wallMaterial), false);
  sideWall.position.set(-11.8, 4.7, -1.5);
  scene.add(sideWall);

  const exterior = new THREE.Group();
  const cityMaterial = new THREE.MeshStandardMaterial({ color: 0x101b22, roughness: 0.98 });
  for (let index = 0; index < 18; index += 1) {
    const width = 0.9 + seeded(index, 83) * 1.7;
    const height = 2 + seeded(index, 89) * 5.8;
    const building = new THREE.Mesh(new THREE.BoxGeometry(width, height, 1.2), cityMaterial);
    building.position.set(-10 + index * 1.18, -0.8 + height / 2, -12.4 - seeded(index, 97) * 3.5);
    exterior.add(building);
    if (index % 2 === 0) {
      const window = new THREE.Mesh(
        new THREE.PlaneGeometry(width * 0.45, height * 0.12),
        new THREE.MeshBasicMaterial({ color: index % 4 ? 0xd5a15f : 0x6e9eb8, transparent: true, opacity: 0.34 }),
      );
      window.position.set(building.position.x, building.position.y + height * 0.12, building.position.z + 0.62);
      exterior.add(window);
    }
  }
  scene.add(exterior);

  const windowGlass = new THREE.Mesh(
    new THREE.PlaneGeometry(19, 10.5),
    new THREE.MeshPhysicalMaterial({
      color: 0x9ab3c0,
      transparent: true,
      opacity: 0.13,
      transmission: 0.2,
      roughness: 0.2,
      metalness: 0.08,
      clearcoat: 1,
      depthWrite: false,
    }),
  );
  windowGlass.position.set(0.8, 5.3, -11.65);
  scene.add(windowGlass);
  const rainMaterial = makeRainMaterial(THREE);
  const rain = new THREE.Mesh(new THREE.PlaneGeometry(19, 10.5), rainMaterial);
  rain.position.set(0.8, 5.3, -11.52);
  rain.renderOrder = 2;
  scene.add(rain);

  const frameMaterial = new THREE.MeshPhysicalMaterial({ color: 0x151617, metalness: 0.72, roughness: 0.3, clearcoat: 0.35 });
  for (const [x, y, width, height] of [
    [-8.8, 5.3, 0.34, 11.1], [10.4, 5.3, 0.34, 11.1], [0.8, 5.3, 0.28, 11.1],
    [0.8, 10.65, 19.5, 0.34], [0.8, -0.05, 19.5, 0.34], [0.8, 5.3, 19.5, 0.24],
  ]) {
    const frame = shadowed(new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.28), frameMaterial));
    frame.position.set(x, y, -11.32);
    scene.add(frame);
  }

  const deskMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x5c3822,
    map: woodTexture,
    bumpMap: woodTexture,
    bumpScale: 0.12,
    roughness: 0.63,
    clearcoat: 0.26,
    clearcoatRoughness: 0.42,
    envMapIntensity: 0.62,
  });
  const desk = shadowed(new THREE.Mesh(new THREE.BoxGeometry(17.5, 0.62, 8.5), deskMaterial));
  desk.position.set(0, -0.45, -2.7);
  scene.add(desk);
  for (const x of [-6.7, 6.7]) {
    const leg = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.72, 4.2, 1.1), deskMaterial));
    leg.position.set(x, -2.55, -2.9);
    scene.add(leg);
  }
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.12, -3), [5.5, 2.3], 0.4);

  const metal = new THREE.MeshPhysicalMaterial({ color: 0x7a5c35, metalness: 0.83, roughness: 0.28, clearcoat: 0.4 });
  const stem = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.14, 3.7, 16), metal));
  stem.position.set(-5.25, 1.75, -4.1);
  scene.add(stem);
  const shade = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(0.72, 1.35, 1.15, 28, 1, true),
    new THREE.MeshPhysicalMaterial({ color: 0x5a3a23, roughness: 0.66, side: THREE.DoubleSide }),
  ));
  shade.position.set(-5.25, 3.5, -4.1);
  scene.add(shade);
  const lamp = new THREE.PointLight(0xffbd68, 17, 16, 2);
  lamp.position.set(-5.25, 3.0, -3.55);
  lamp.castShadow = true;
  lamp.shadow.mapSize.set(mobile ? 256 : 768, mobile ? 256 : 768);
  scene.add(lamp);

  const dust = makeParticles(THREE, mobile ? 80 : 190, { x: [-8, 8], y: [0, 7], z: [-10, 2] }, 0xffdfaa, 0.035, 0.19, 103);
  scene.add(dust.points);
  pack.particles.push(dust);
  const coolTop = new THREE.Color(0x0b1219);
  const deepTop = new THREE.Color(0x05090d);
  pack.update = (time, state, motion) => {
    const darkness = 0.25 + state.elapsed * 0.75;
    pack.sky.uniforms.topColor.value.copy(coolTop).lerp(deepTop, darkness * 0.65);
    pack.keyLight.intensity = 0.75 - state.elapsed * 0.28;
    lamp.intensity = 13 + state.elapsed * 10 + Math.sin(time * 1.1) * 0.24 * motion;
    rainMaterial.uniforms.time.value = time * motion;
    rainMaterial.uniforms.strength.value = 0.25 + state.density * 0.2;
    dust.points.rotation.y = time * 0.006 * motion;
  };
  return pack;
}

function buildForest(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "foret", {
    fog: 0x13251d,
    fogDensity: 0.028,
    groundLight: 0x08100b,
    hemisphere: 0.86,
    keyIntensity: 3.6,
    sky: { top: 0x07150f, horizon: 0x294a36, ground: 0x07100b, light: 0xe8f1c4, stars: 0 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.8 : 4.4, mobile ? 15.2 : 16.8);
  pack.target.set(0, 1.4, -8.3);
  const mossTexture = makeSurfaceTexture(THREE, 0x283f2b, "stone", mobile);
  const barkTexture = makeSurfaceTexture(THREE, 0x3c2d21, "bark", mobile);
  const stoneTexture = makeSurfaceTexture(THREE, 0x35423b, "stone", mobile);
  pack.textures.push(mossTexture, barkTexture, stoneTexture);

  const ground = shadowed(new THREE.Mesh(
    new THREE.PlaneGeometry(52, 70, 1, 1),
    new THREE.MeshStandardMaterial({ color: 0x263a29, map: mossTexture, bumpMap: mossTexture, bumpScale: 0.23, roughness: 0.98 }),
  ), false);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -1.15, -16);
  scene.add(ground);

  const slab = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.6, 5.1, 0.48, 48),
    new THREE.MeshPhysicalMaterial({ color: 0x384640, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.18, roughness: 0.86, clearcoat: 0.16 }),
  ));
  slab.scale.z = 0.72;
  slab.position.set(0, -0.8, -3.4);
  scene.add(slab);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.54, -3.2), [5.5, 2.4], 0.45);

  const bark = new THREE.MeshStandardMaterial({ color: 0x493528, map: barkTexture, bumpMap: barkTexture, bumpScale: 0.3, roughness: 0.98 });
  const canopy = new THREE.MeshStandardMaterial({ color: 0x1f3826, roughness: 0.93 });
  const trunkCount = mobile ? 18 : 28;
  for (let index = 0; index < trunkCount; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (4.3 + seeded(index, 121) * 13.5);
    const z = 1 - seeded(index, 127) * 42;
    const radius = 0.45 + seeded(index, 131) * 1.2;
    const height = 10 + seeded(index, 137) * 15;
    const trunk = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.74, radius, height, 12), bark));
    trunk.position.set(x, -1.15 + height / 2, z);
    trunk.rotation.z = (seeded(index, 139) - 0.5) * 0.08;
    scene.add(trunk);
    const crown = shadowed(new THREE.Mesh(new THREE.IcosahedronGeometry(radius * 2.9, 1), canopy));
    crown.scale.set(1.35, 0.75, 1.1);
    crown.position.set(x, height - 0.4, z);
    scene.add(crown);
  }

  const rockMaterial = new THREE.MeshStandardMaterial({ color: 0x2d3833, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.16, roughness: 1 });
  const rocks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.65, 0), rockMaterial, mobile ? 24 : 42);
  const transform = new THREE.Object3D();
  for (let index = 0; index < rocks.count; index += 1) {
    const side = index % 2 ? 1 : -1;
    transform.position.set(side * (3.9 + seeded(index, 149) * 14), -0.86, 2 - seeded(index, 151) * 34);
    const scale = 0.3 + seeded(index, 157) * 1.5;
    transform.scale.set(scale * 1.4, scale * 0.7, scale);
    transform.rotation.set(seeded(index, 163) * TAU, seeded(index, 167) * TAU, seeded(index, 173) * TAU);
    transform.updateMatrix();
    rocks.setMatrixAt(index, transform.matrix);
  }
  rocks.castShadow = true;
  rocks.receiveShadow = true;
  scene.add(rocks);

  const shafts = [];
  for (let index = 0; index < 4; index += 1) {
    const material = new THREE.MeshBasicMaterial({
      color: 0xe8f4c6,
      transparent: true,
      opacity: 0.035,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    });
    const shaft = new THREE.Mesh(new THREE.ConeGeometry(2.2 + index * 0.4, 19, 24, 1, true), material);
    shaft.position.set(-6 + index * 4.2, 8.3, -12 - index * 3.4);
    shaft.rotation.z = -0.12 + index * 0.04;
    scene.add(shaft);
    shafts.push(shaft);
  }
  const spores = makeParticles(THREE, mobile ? 140 : 360, { x: [-15, 15], y: [-0.2, 10], z: [-32, 2] }, 0xdff2bf, 0.045, 0.22, 181);
  scene.add(spores.points);
  pack.particles.push(spores);
  pack.update = (time, state, motion) => {
    pack.keyLight.position.x = -13 + state.elapsed * 10;
    pack.keyLight.intensity = 3.2 - state.elapsed * 0.7;
    scene.fog.density = 0.025 + state.elapsed * 0.006;
    for (let index = 0; index < shafts.length; index += 1) {
      shafts[index].position.x += Math.sin(time * 0.12 + index) * 0.0015 * motion;
      shafts[index].material.opacity = 0.026 + state.elapsed * 0.026;
    }
    spores.points.position.y = Math.sin(time * 0.17) * 0.16 * motion;
    spores.points.rotation.y = time * 0.004 * motion;
  };
  return pack;
}

function makeOceanMaterial(THREE, colors) {
  return new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      motion: { value: 1 },
      deepColor: { value: new THREE.Color(colors.deep) },
      surfaceColor: { value: new THREE.Color(colors.surface) },
      lightColor: { value: new THREE.Color(colors.light) },
    },
    vertexShader: `
      uniform float time;
      uniform float motion;
      varying float vWave;
      varying vec3 vWorld;
      void main(){
        vec3 p=position;
        float wave=sin(p.x*.24+time*.72)+sin(p.y*.38-time*.53)*.48+sin((p.x+p.y)*.11+time*.31)*.62;
        p.z+=wave*.22*motion;
        vWave=wave;
        vec4 world=modelMatrix*vec4(p,1.0);
        vWorld=world.xyz;
        gl_Position=projectionMatrix*viewMatrix*world;
      }
    `,
    fragmentShader: `
      varying float vWave;
      varying vec3 vWorld;
      uniform float time;
      uniform vec3 deepColor;
      uniform vec3 surfaceColor;
      uniform vec3 lightColor;
      void main(){
        vec3 viewDir=normalize(cameraPosition-vWorld);
        float fresnel=pow(1.0-max(viewDir.y,0.0),2.4);
        float crest=smoothstep(.85,1.75,vWave);
        float longFlow=pow(.5+.5*sin(vWorld.z*1.18-time*1.55+sin(vWorld.x*.72)),7.0);
        float crossRipple=pow(.5+.5*sin(vWorld.x*2.25+vWorld.z*.23+time*.74),12.0);
        vec3 color=mix(deepColor,surfaceColor,.34+fresnel*.45);
        color+=lightColor*(crest*.22+longFlow*.07+crossRipple*.035);
        gl_FragColor=vec4(color,1.0);
      }
    `,
  });
}

function buildOcean(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "ocean", {
    fog: 0x7895a1,
    fogDensity: 0.008,
    groundLight: 0x14252a,
    hemisphere: 1.5,
    keyIntensity: 4.2,
    sky: { top: 0x547d99, horizon: 0xb4c6c8, ground: 0x31596a, light: 0xffe2b8, stars: 0 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 4.5 : 5.0, mobile ? 15.5 : 17.5);
  pack.target.set(0, 0.8, -10);
  const rockTexture = makeSurfaceTexture(THREE, 0x384449, "stone", mobile);
  pack.textures.push(rockTexture);

  const oceanMaterial = makeOceanMaterial(THREE, { deep: 0x0a3343, surface: 0x39778a, light: 0xd9f0ed });
  const ocean = new THREE.Mesh(new THREE.PlaneGeometry(90, 90, mobile ? 70 : 120, mobile ? 70 : 120), oceanMaterial);
  ocean.rotation.x = -Math.PI / 2;
  ocean.position.set(0, -2.2, -25);
  scene.add(ocean);

  const rockMaterial = new THREE.MeshStandardMaterial({ color: 0x374247, map: rockTexture, bumpMap: rockTexture, bumpScale: 0.22, roughness: 0.97 });
  const ledge = shadowed(new THREE.Mesh(new THREE.BoxGeometry(24, 2.1, 13), rockMaterial));
  ledge.position.set(0, -1.48, 0.8);
  ledge.rotation.y = -0.035;
  scene.add(ledge);
  const slab = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.4, 4.9, 0.36, 48),
    new THREE.MeshPhysicalMaterial({ color: 0x465257, map: rockTexture, bumpMap: rockTexture, bumpScale: 0.1, roughness: 0.82, clearcoat: 0.18 }),
  ));
  slab.scale.z = 0.74;
  slab.position.set(0, -0.28, -3.0);
  scene.add(slab);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.08, -2.9), [5.4, 2.3], 0.46);

  const formations = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1.45, 1), rockMaterial, mobile ? 28 : 46);
  const transform = new THREE.Object3D();
  for (let index = 0; index < formations.count; index += 1) {
    const distant = index > formations.count * 0.55;
    const side = index % 2 ? 1 : -1;
    const x = distant ? side * (12 + seeded(index, 193) * 20) : side * (7 + seeded(index, 197) * 8);
    const z = distant ? -17 - seeded(index, 199) * 28 : 4 - seeded(index, 211) * 14;
    const scale = distant ? 1 + seeded(index, 223) * 3.7 : 0.7 + seeded(index, 227) * 2.0;
    transform.position.set(x, -2 + scale * 0.28, z);
    transform.scale.set(scale * 1.5, scale, scale * 1.25);
    transform.rotation.set(seeded(index, 229) * TAU, seeded(index, 233) * TAU, seeded(index, 239) * TAU);
    transform.updateMatrix();
    formations.setMatrixAt(index, transform.matrix);
  }
  formations.castShadow = true;
  formations.receiveShadow = true;
  scene.add(formations);

  const mist = makeParticles(THREE, mobile ? 100 : 260, { x: [-24, 24], y: [-1.4, 3.5], z: [-44, -8] }, 0xd5e9e9, 0.08, 0.16, 241);
  scene.add(mist.points);
  pack.particles.push(mist);
  const dayTop = new THREE.Color(0x547d99);
  const duskTop = new THREE.Color(0x26394b);
  const dayHorizon = new THREE.Color(0xb4c6c8);
  const amberHorizon = new THREE.Color(0xd09b76);
  pack.update = (time, state, motion) => {
    oceanMaterial.uniforms.time.value = time;
    oceanMaterial.uniforms.motion.value = 0.45 + motion * (1 - state.elapsed * 0.32);
    pack.sky.uniforms.topColor.value.copy(dayTop).lerp(duskTop, state.elapsed * 0.48);
    pack.sky.uniforms.horizonColor.value.copy(dayHorizon).lerp(amberHorizon, state.elapsed * 0.38);
    pack.keyLight.position.x = -14 + state.elapsed * 22;
    pack.keyLight.position.y = 18 - state.elapsed * 7;
    scene.fog.density = 0.007 + state.elapsed * 0.003;
    mist.points.position.x = Math.sin(time * 0.035) * 1.2 * motion;
  };
  return pack;
}

function duneHeight(x, z) {
  const longWave = Math.sin(x * 0.12 + z * 0.075) * 1.32;
  const crossing = Math.sin(x * 0.075 - z * 0.155 + 1.7) * 0.68;
  const crest = Math.pow(0.5 + 0.5 * Math.sin(x * 0.22 + z * 0.105 + 0.8), 3.2) * 1.28;
  return longWave + crossing + crest - 0.52;
}

function buildSahara(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "sahara", {
    fog: 0xb87952,
    fogDensity: 0.016,
    groundLight: 0x492717,
    hemisphere: 1.55,
    keyIntensity: 4.3,
    sky: { top: 0x365d82, horizon: 0xe4a061, ground: 0x6f3f29, light: 0xffe4b0, stars: 0 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0.2, mobile ? 3.8 : 4.2, mobile ? 14.8 : 16.2);
  pack.target.set(0.4, 1.2, -11.8);
  const sandTexture = makeSurfaceTexture(THREE, 0xd18a48, "sand", mobile);
  const stoneTexture = makeSurfaceTexture(THREE, 0x6a5140, "stone", mobile);
  pack.textures.push(sandTexture, stoneTexture);

  const geometry = new THREE.PlaneGeometry(58, 72, mobile ? 72 : 128, mobile ? 88 : 148);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const z = -position.getY(index);
    position.setZ(index, duneHeight(x, z));
  }
  geometry.computeVertexNormals();
  geometry.rotateX(-Math.PI / 2);
  const dunes = shadowed(new THREE.Mesh(
    geometry,
    new THREE.MeshPhysicalMaterial({ color: 0xd18a48, map: sandTexture, bumpMap: sandTexture, bumpScale: 0.08, roughness: 0.9, clearcoat: 0.06 }),
  ), false);
  dunes.position.z = -14;
  scene.add(dunes);

  const focusStone = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.3, 4.8, 0.34, 56),
    new THREE.MeshStandardMaterial({ color: 0x8a5b3d, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.13, roughness: 0.91 }),
  ));
  focusStone.scale.z = 0.72;
  focusStone.position.set(0, -0.1, -3.1);
  scene.add(focusStone);
  addContactShadow(THREE, pack, new THREE.Vector3(0, 0.09, -3), [5.3, 2.2], 0.38);

  const stone = new THREE.MeshPhysicalMaterial({ color: 0x6a5140, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.16, roughness: 0.9 });
  const bronze = new THREE.MeshPhysicalMaterial({ color: 0x6b4529, metalness: 0.88, roughness: 0.3, clearcoat: 0.54 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x82b7bd, roughness: 0.12, transmission: 0.45, thickness: 0.7, transparent: true, opacity: 0.64, clearcoat: 1, side: THREE.DoubleSide });
  const observatory = new THREE.Group();
  observatory.position.set(7.4, 0.2, -15.2);
  const base = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.7, 1.0, 40), stone));
  const dome = shadowed(new THREE.Mesh(new THREE.SphereGeometry(2.45, 48, 24, 0, TAU, 0, Math.PI / 2), glass));
  dome.position.y = 0.72;
  const ring = shadowed(new THREE.Mesh(new THREE.TorusGeometry(2.48, 0.1, 10, 72), bronze));
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.73;
  const meridian = shadowed(new THREE.Mesh(new THREE.TorusGeometry(4.2, 0.2, 12, 90, Math.PI * 1.58), bronze));
  meridian.position.y = 3.05;
  meridian.rotation.z = -0.3;
  observatory.add(base, dome, ring, meridian);
  scene.add(observatory);
  const observatoryLight = new THREE.PointLight(0xffa751, 4, 17, 2);
  observatoryLight.position.set(7.4, 1.8, -13.5);
  scene.add(observatoryLight);

  const dust = makeParticles(THREE, mobile ? 320 : 820, { x: [-26, 26], y: [0.1, 5.2], z: [-48, 8] }, 0xe7a65f, 0.055, 0.16, 257);
  scene.add(dust.points);
  pack.particles.push(dust);
  const dayTop = new THREE.Color(0x365d82);
  const duskTop = new THREE.Color(0x293650);
  const nightTop = new THREE.Color(0x030711);
  const dayHorizon = new THREE.Color(0xe4a061);
  const duskHorizon = new THREE.Color(0xd66f4d);
  const nightHorizon = new THREE.Color(0x33253b);
  pack.update = (time, state, motion) => {
    const twilight = clamp(state.elapsed * 1.22);
    const night = smoothstep(0.64, 1, state.elapsed);
    pack.sky.uniforms.topColor.value.copy(dayTop).lerp(duskTop, twilight).lerp(nightTop, night);
    pack.sky.uniforms.horizonColor.value.copy(dayHorizon).lerp(duskHorizon, twilight).lerp(nightHorizon, night);
    pack.sky.uniforms.starStrength.value = night * 1.2;
    pack.keyLight.position.set(-16 + state.elapsed * 27, 17 - state.elapsed * 12, 8);
    pack.keyLight.intensity = 4.3 - state.elapsed * 3.2;
    pack.hemisphere.intensity = 1.55 - state.elapsed * 1.1;
    observatoryLight.intensity = 3 + state.elapsed * 14;
    scene.fog.density = 0.012 + state.elapsed * 0.007;
    dust.points.position.x = ((time * 0.22 * motion) % 4) - 2;
  };
  return pack;
}

function makeAuroraMaterial(THREE, color, phase) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    uniforms: {
      time: { value: phase },
      strength: { value: 0.3 },
      color: { value: new THREE.Color(color) },
    },
    vertexShader: `
      varying vec2 vUv;
      uniform float time;
      void main(){
        vUv=uv;
        vec3 p=position;
        p.x+=sin(uv.y*8.0+time*.32+uv.x*3.0)*.36;
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform float time;
      uniform float strength;
      uniform vec3 color;
      void main(){
        float wave=sin(vUv.x*15.0+sin(vUv.y*5.0+time*.3)*2.2+time)*.5+.5;
        float folds=smoothstep(.2,.95,wave);
        float vertical=smoothstep(0.0,.16,vUv.y)*(1.0-smoothstep(.72,1.0,vUv.y));
        float edge=smoothstep(0.0,.13,vUv.x)*(1.0-smoothstep(.82,1.0,vUv.x));
        gl_FragColor=vec4(color,(.12+folds*.44)*vertical*edge*strength);
      }
    `,
  });
}

function buildAurora(THREE, mobile, environmentTexture) {
  const pack = createPack(THREE, "aurores", {
    fog: 0x0c2732,
    fogDensity: 0.012,
    groundLight: 0x102b35,
    hemisphere: 1.0,
    keyIntensity: 2.4,
    sky: { top: 0x020813, horizon: 0x123b4d, ground: 0x07141b, light: 0xcaf8ec, stars: 0.8 },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 4.2 : 4.8, mobile ? 15.2 : 17.0);
  pack.target.set(0, 1.2, -9.5);
  const snowTexture = makeSurfaceTexture(THREE, 0xdde8e8, "snow", mobile);
  const rockTexture = makeSurfaceTexture(THREE, 0x34444c, "stone", mobile);
  pack.textures.push(snowTexture, rockTexture);

  const snowMaterial = new THREE.MeshPhysicalMaterial({ color: 0xdce7e7, map: snowTexture, bumpMap: snowTexture, bumpScale: 0.045, roughness: 0.76, clearcoat: 0.2 });
  const ground = shadowed(new THREE.Mesh(new THREE.PlaneGeometry(52, 64), snowMaterial), false);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -1.15, -15);
  scene.add(ground);
  const lake = new THREE.Mesh(
    new THREE.PlaneGeometry(32, 22),
    new THREE.MeshPhysicalMaterial({ color: 0x123e4a, roughness: 0.12, metalness: 0.24, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 0.85 }),
  );
  lake.rotation.x = -Math.PI / 2;
  lake.position.set(0, -1.0, -23);
  scene.add(lake);
  const slab = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(4.5, 5.0, 0.38, 48),
    new THREE.MeshPhysicalMaterial({ color: 0xcbd7d8, map: snowTexture, bumpMap: snowTexture, bumpScale: 0.05, roughness: 0.72, clearcoat: 0.24 }),
  ));
  slab.scale.z = 0.72;
  slab.position.set(0, -0.78, -3.2);
  scene.add(slab);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.57, -3.1), [5.4, 2.3], 0.28);

  const rock = new THREE.MeshStandardMaterial({ color: 0x34444c, map: rockTexture, bumpMap: rockTexture, bumpScale: 0.16, roughness: 0.94 });
  for (let index = 0; index < 11; index += 1) {
    const x = -22 + index * 4.5 + (seeded(index, 269) - 0.5) * 2.4;
    const height = 5 + seeded(index, 271) * 8.8;
    const radius = 2.5 + seeded(index, 277) * 3.8;
    const mountain = shadowed(new THREE.Mesh(new THREE.ConeGeometry(radius, height, 7), rock), false);
    mountain.position.set(x, -0.9 + height / 2, -28 - seeded(index, 281) * 11);
    mountain.rotation.y = seeded(index, 283) * TAU;
    scene.add(mountain);
    const cap = shadowed(new THREE.Mesh(new THREE.ConeGeometry(radius * 0.59, height * 0.38, 7), snowMaterial), false);
    cap.position.set(x, mountain.position.y + height * 0.31, mountain.position.z);
    cap.rotation.y = mountain.rotation.y;
    scene.add(cap);
  }

  const auroras = [];
  for (let index = 0; index < 4; index += 1) {
    const material = makeAuroraMaterial(THREE, index % 2 ? 0x69b9ff : 0x65ffc2, index * 1.7);
    const ribbon = new THREE.Mesh(new THREE.PlaneGeometry(18, 18, 30, 30), material);
    ribbon.position.set(-11 + index * 7, 12 + index * 0.6, -39 - index * 2.4);
    ribbon.rotation.z = -0.1 + index * 0.035;
    ribbon.rotation.y = (index - 1.5) * 0.08;
    scene.add(ribbon);
    auroras.push(ribbon);
  }
  const snow = makeParticles(THREE, mobile ? 260 : 680, { x: [-25, 25], y: [-0.2, 18], z: [-45, 8] }, 0xe9fbff, 0.065, 0.38, 293);
  scene.add(snow.points);
  pack.particles.push(snow);
  const darkTop = new THREE.Color(0x020813);
  const deeperTop = new THREE.Color(0x01040a);
  pack.update = (time, state, motion) => {
    const intensity = 0.22 + state.elapsed * 0.65;
    for (let index = 0; index < auroras.length; index += 1) {
      auroras[index].material.uniforms.time.value = time * motion + index * 1.7;
      auroras[index].material.uniforms.strength.value = intensity;
    }
    pack.sky.uniforms.topColor.value.copy(darkTop).lerp(deeperTop, state.elapsed * 0.55);
    pack.sky.uniforms.starStrength.value = 0.58 + state.elapsed * 0.4;
    pack.keyLight.intensity = 2.25 - state.elapsed * 0.55;
    lake.material.roughness = 0.11 + Math.sin(time * 0.1) * 0.01 * motion;
    snow.points.position.y = -((time * 0.23 * motion) % 2.2);
    snow.points.position.x = Math.sin(time * 0.12) * 0.7 * motion;
  };
  return pack;
}

function makeRadialTexture(THREE, colors) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(128, 128, 0, 128, 128, 128);
  colors.forEach(([stop, color]) => gradient.addColorStop(stop, color));
  context.fillStyle = gradient;
  context.fillRect(0, 0, 256, 256);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function buildCosmos(THREE, mobile, environmentTexture, key = "galaxie") {
  const interstellar = key === "interstellaire";
  const pack = createPack(THREE, key, {
    fog: interstellar ? 0x060b18 : 0x080312,
    fogDensity: interstellar ? 0.0035 : 0.0022,
    groundLight: 0x010208,
    hemisphere: 0.42,
    keyIntensity: 1.25,
    sky: {
      top: interstellar ? 0x01040d : 0x03010a,
      horizon: interstellar ? 0x101a35 : 0x241039,
      ground: 0x020208,
      light: interstellar ? 0xbfd7ff : 0xf1d5ff,
      stars: 1.25,
    },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 3.8 : 4.4, mobile ? 15.8 : 17.2);
  pack.target.set(0, 1.5, -13);
  const deckTexture = makeSurfaceTexture(THREE, 0x262a38, "stone", mobile);
  pack.textures.push(deckTexture);

  const deckMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x202633,
    map: deckTexture,
    bumpMap: deckTexture,
    bumpScale: 0.08,
    metalness: 0.66,
    roughness: 0.34,
    clearcoat: 0.46,
    clearcoatRoughness: 0.2,
    envMapIntensity: 0.95,
  });
  const deck = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(6.1, 6.5, 0.48, 64), deckMaterial));
  deck.scale.z = 0.64;
  deck.position.set(0, -0.68, -3.4);
  scene.add(deck);
  const deckRim = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(4.05, 0.075, 10, 96),
    new THREE.MeshPhysicalMaterial({ color: 0x6d7791, metalness: 0.92, roughness: 0.22, clearcoat: 0.7 }),
  ));
  deckRim.rotation.x = Math.PI / 2;
  deckRim.position.set(0, -0.41, -3.4);
  deckRim.scale.z = 0.64;
  scene.add(deckRim);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.41, -3.2), [5.2, 2.15], 0.5);

  const starCount = mobile ? 1300 : 3200;
  const starPositions = new Float32Array(starCount * 3);
  const starColors = new Float32Array(starCount * 3);
  const cold = new THREE.Color(0xbfd9ff);
  const warm = new THREE.Color(0xffd9b3);
  for (let index = 0; index < starCount; index += 1) {
    starPositions[index * 3] = (seeded(index, 307) - 0.5) * 62;
    starPositions[index * 3 + 1] = 1.5 + seeded(index, 311) * 31;
    starPositions[index * 3 + 2] = -8 - seeded(index, 313) * 76;
    const color = cold.clone().lerp(warm, seeded(index, 317) * 0.34);
    starColors[index * 3] = color.r;
    starColors[index * 3 + 1] = color.g;
    starColors[index * 3 + 2] = color.b;
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  starGeometry.setAttribute("color", new THREE.BufferAttribute(starColors, 3));
  const starMaterial = new THREE.PointsMaterial({
    size: mobile ? 0.065 : 0.052,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
    sizeAttenuation: true,
  });
  const starField = new THREE.Points(starGeometry, starMaterial);
  starField.frustumCulled = false;
  scene.add(starField);

  const galaxyCount = mobile ? 2100 : 5600;
  const galaxyPositions = new Float32Array(galaxyCount * 3);
  const galaxyColors = new Float32Array(galaxyCount * 3);
  const violet = new THREE.Color(0xb982ff);
  const blue = new THREE.Color(0x78b9ff);
  const coreColor = new THREE.Color(0xfff0cf);
  for (let index = 0; index < galaxyCount; index += 1) {
    const radius = Math.pow(seeded(index, 331), 0.72) * 16;
    const arm = index % 4;
    const scatter = (seeded(index, 337) - 0.5) * (0.6 + radius * 0.12);
    const angle = arm * TAU / 4 + radius * 0.48 + scatter;
    galaxyPositions[index * 3] = Math.cos(angle) * radius;
    galaxyPositions[index * 3 + 1] = Math.sin(angle) * radius * 0.52;
    galaxyPositions[index * 3 + 2] = (seeded(index, 347) - 0.5) * (0.45 + radius * 0.055);
    const color = radius < 3 ? coreColor.clone() : violet.clone().lerp(blue, seeded(index, 349));
    galaxyColors[index * 3] = color.r;
    galaxyColors[index * 3 + 1] = color.g;
    galaxyColors[index * 3 + 2] = color.b;
  }
  const galaxyGeometry = new THREE.BufferGeometry();
  galaxyGeometry.setAttribute("position", new THREE.BufferAttribute(galaxyPositions, 3));
  galaxyGeometry.setAttribute("color", new THREE.BufferAttribute(galaxyColors, 3));
  const galaxyMaterial = new THREE.PointsMaterial({
    size: mobile ? 0.095 : 0.072,
    vertexColors: true,
    transparent: true,
    opacity: interstellar ? 0.38 : 0.82,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });
  const galaxy = new THREE.Points(galaxyGeometry, galaxyMaterial);
  galaxy.position.set(interstellar ? -7 : 3.5, interstellar ? 10 : 8.2, -39);
  galaxy.rotation.set(-0.14, 0.18, -0.24);
  scene.add(galaxy);

  const coreTexture = makeRadialTexture(THREE, [
    [0, "rgba(255,248,222,1)"], [0.13, "rgba(247,211,255,.9)"],
    [0.48, "rgba(137,89,255,.24)"], [1, "rgba(28,12,72,0)"],
  ]);
  pack.textures.push(coreTexture);
  const core = new THREE.Sprite(new THREE.SpriteMaterial({
    map: coreTexture,
    transparent: true,
    opacity: interstellar ? 0.28 : 0.78,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }));
  core.position.copy(galaxy.position);
  core.scale.set(12, 7, 1);
  scene.add(core);

  const planetMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x425b87,
    roughness: 0.72,
    metalness: 0.03,
    clearcoat: 0.16,
    emissive: 0x071020,
    emissiveIntensity: 0.32,
  });
  const planet = new THREE.Group();
  const planetBody = new THREE.Mesh(new THREE.SphereGeometry(6.8, mobile ? 32 : 64, mobile ? 20 : 40), planetMaterial);
  const planetRing = new THREE.Mesh(
    new THREE.RingGeometry(8.2, 12.8, 96),
    new THREE.MeshPhysicalMaterial({ color: 0xb8a787, transparent: true, opacity: 0.58, side: THREE.DoubleSide, roughness: 0.76, depthWrite: false }),
  );
  planetRing.rotation.x = 1.22;
  planet.add(planetBody, planetRing);
  planet.position.set(8.7, 6.7, -31);
  planet.rotation.z = -0.21;
  planet.visible = interstellar;
  scene.add(planet);

  const navigationLights = [];
  for (const x of [-4.65, 4.65]) {
    const light = new THREE.PointLight(x < 0 ? 0x66aaff : 0xff687d, 2.2, 5, 2);
    light.position.set(x, -0.18, -3.3);
    scene.add(light);
    navigationLights.push(light);
  }
  pack.update = (time, state, motion) => {
    galaxy.rotation.z = -0.24 + time * 0.008 * motion;
    galaxyMaterial.opacity = (interstellar ? 0.32 : 0.72) + state.elapsed * (interstellar ? 0.12 : 0.2);
    core.material.opacity = (interstellar ? 0.22 : 0.66) + state.elapsed * (interstellar ? 0.14 : 0.2);
    const pulse = 1 + Math.sin(time * 0.42) * 0.035 * motion;
    core.scale.set(12 * pulse, 7 * pulse, 1);
    starField.rotation.y = time * 0.0025 * motion;
    planet.rotation.y = time * 0.014 * motion;
    navigationLights.forEach((light, index) => { light.intensity = 1.7 + Math.sin(time * 1.4 + index * 2.1) * 0.45 * motion; });
    pack.sky.uniforms.starStrength.value = 0.9 + state.elapsed * 0.32;
  };
  return pack;
}

function buildTimeRiver(THREE, mobile, environmentTexture, key = "fleuve_temps") {
  const fountain = key === "fontaine";
  const abyss = key === "abysses";
  const pack = createPack(THREE, key, {
    fog: abyss ? 0x06323a : fountain ? 0x174f5d : 0x252f58,
    fogDensity: abyss ? 0.025 : 0.015,
    groundLight: abyss ? 0x021012 : 0x090a17,
    hemisphere: abyss ? 0.72 : 1.05,
    keyIntensity: abyss ? 1.8 : 2.8,
    sky: {
      top: abyss ? 0x021116 : fountain ? 0x061724 : 0x060b1c,
      horizon: abyss ? 0x0d4b55 : fountain ? 0x1f7180 : 0x354e8b,
      ground: abyss ? 0x020b0e : 0x080a16,
      light: abyss ? 0x9ff8ee : fountain ? 0xdffff7 : 0xf2d6a0,
      stars: abyss ? 0 : 0.45,
    },
  }, mobile, environmentTexture);
  const { scene } = pack;
  pack.camera.position.set(0, mobile ? 4.0 : 4.6, mobile ? 15.5 : 17.0);
  pack.target.set(0, 1.0, -11.5);
  const stoneTexture = makeSurfaceTexture(THREE, abyss ? 0x17464a : 0x44485b, "stone", mobile);
  stoneTexture.repeat.set(6, 14);
  pack.textures.push(stoneTexture);
  const stone = new THREE.MeshStandardMaterial({
    color: abyss ? 0x28565a : fountain ? 0x576a6c : 0x626779,
    map: stoneTexture,
    bumpMap: stoneTexture,
    bumpScale: 0.28,
    roughness: 0.88,
    metalness: 0.015,
    envMapIntensity: 0.34,
  });

  const riverMaterial = makeOceanMaterial(THREE, {
    deep: abyss ? 0x031a20 : fountain ? 0x073b45 : 0x111d4a,
    surface: abyss ? 0x16717a : fountain ? 0x23a4aa : 0x5679ce,
    light: abyss ? 0x8ff5e6 : fountain ? 0xc9fff7 : 0xe7d5ff,
  });
  const river = new THREE.Mesh(new THREE.PlaneGeometry(13, 88, mobile ? 34 : 62, mobile ? 80 : 136), riverMaterial);
  river.rotation.x = -Math.PI / 2;
  river.position.set(0, -1.28, -30);
  scene.add(river);

  // Les rives sont de vrais reliefs irréguliers. Deux pavés rectangulaires lisaient
  // comme un décor de jeu ancien et coupaient brutalement l'eau.
  for (const side of [-1, 1]) {
    const geometry = new THREE.PlaneGeometry(16, 88, mobile ? 18 : 32, mobile ? 48 : 80);
    const positions = geometry.attributes.position;
    for (let index = 0; index < positions.count; index += 1) {
      const localX = positions.getX(index);
      const localZ = positions.getY(index);
      const fromWater = side < 0 ? 8 - localX : localX + 8;
      const distance = clamp(fromWater / 16, 0, 1);
      const broad = Math.sin(localZ * 0.16 + side * 1.7) * 0.16 + Math.sin(localX * 0.62 - localZ * 0.07) * 0.1;
      const fracture = (seeded(index, 449 + side * 7) - 0.5) * (0.08 + distance * 0.28);
      positions.setZ(index, -1.06 + Math.pow(distance, 0.72) * 1.22 + broad + fracture);
    }
    geometry.computeVertexNormals();
    const bank = shadowed(new THREE.Mesh(geometry, stone), false);
    bank.rotation.x = -Math.PI / 2;
    bank.position.set(side * 14, 0, -30);
    scene.add(bank);
  }
  const riverRocks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.78, 1), stone, mobile ? 44 : 82);
  const rockTransform = new THREE.Object3D();
  for (let index = 0; index < riverRocks.count; index += 1) {
    const side = index % 2 ? 1 : -1;
    const radius = 7.2 + seeded(index, 457) * 7.8;
    rockTransform.position.set(side * radius, -0.72 + seeded(index, 461) * 0.78, -7 - seeded(index, 463) * 65);
    const scale = 0.42 + seeded(index, 467) * 1.22;
    rockTransform.scale.set(scale * (0.8 + seeded(index, 469)), scale * (0.45 + seeded(index, 471) * 0.72), scale);
    rockTransform.rotation.set(seeded(index, 475) * 1.4, seeded(index, 479) * TAU, seeded(index, 487) * 0.52);
    rockTransform.updateMatrix();
    riverRocks.setMatrixAt(index, rockTransform.matrix);
  }
  riverRocks.castShadow = true;
  riverRocks.receiveShadow = true;
  scene.add(riverRocks);
  const bridge = shadowed(new THREE.Mesh(
    new THREE.BoxGeometry(10.8, 0.48, 5.5),
    new THREE.MeshPhysicalMaterial({ color: abyss ? 0x315f61 : 0x555b6d, map: stoneTexture, bumpMap: stoneTexture, bumpScale: 0.18, roughness: 0.8, clearcoat: 0.12, envMapIntensity: 0.42 }),
  ));
  bridge.position.set(0, -0.72, -3.2);
  scene.add(bridge);
  addContactShadow(THREE, pack, new THREE.Vector3(0, -0.46, -3.1), [5.5, 2.25], 0.44);

  const ruins = new THREE.Group();
  const columnStone = new THREE.BoxGeometry(0.72, 0.7, 0.82, 2, 2, 2);
  const archStone = new THREE.BoxGeometry(0.7, 0.5, 0.88, 2, 2, 2);
  for (let index = 0; index < 6; index += 1) {
    const side = index % 2 ? 1 : -1;
    const x = side * (7.8 + seeded(index, 367) * 2.6);
    const z = -9 - index * 8.3;
    const height = 3.2 + seeded(index, 373) * 2.4;
    for (const offset of [-1.75, 1.75]) {
      const blocks = Math.max(4, Math.round(height / 0.68));
      for (let blockIndex = 0; blockIndex < blocks; blockIndex += 1) {
        const block = shadowed(new THREE.Mesh(columnStone, stone));
        block.position.set(
          x + offset + (seeded(blockIndex + index * 13, 491) - 0.5) * 0.12,
          -0.72 + blockIndex * 0.68 + 0.35,
          z + (seeded(blockIndex + index * 11, 499) - 0.5) * 0.12,
        );
        block.rotation.y = (seeded(blockIndex + index * 17, 503) - 0.5) * 0.16;
        ruins.add(block);
      }
    }
    for (let blockIndex = 0; blockIndex <= 12; blockIndex += 1) {
      const angle = Math.PI * blockIndex / 12;
      const block = shadowed(new THREE.Mesh(archStone, stone));
      block.position.set(x + Math.cos(angle) * 1.76, -0.55 + height + Math.sin(angle) * 1.76, z);
      block.rotation.z = angle - Math.PI / 2;
      block.rotation.y = (seeded(blockIndex + index * 19, 509) - 0.5) * 0.1;
      ruins.add(block);
    }
  }
  scene.add(ruins);

  const shardMaterial = new THREE.MeshPhysicalMaterial({
    color: abyss ? 0x7df5e5 : 0xbccfff,
    emissive: abyss ? 0x27bcae : 0x567dff,
    emissiveIntensity: 0.9,
    metalness: 0.08,
    roughness: 0.18,
    transparent: true,
    opacity: 0.62,
    transmission: 0.24,
    depthWrite: false,
  });
  const shards = new THREE.Group();
  const shardCount = mobile ? 18 : 36;
  for (let index = 0; index < shardCount; index += 1) {
    const shard = new THREE.Mesh(new THREE.OctahedronGeometry(0.13 + seeded(index, 379) * 0.24, 0), shardMaterial);
    shard.position.set((seeded(index, 383) - 0.5) * 10, 0.2 + seeded(index, 389) * 5.8, -6 - seeded(index, 397) * 46);
    shard.scale.y = 2 + seeded(index, 401) * 3.5;
    shard.rotation.set(seeded(index, 409) * TAU, seeded(index, 419) * TAU, seeded(index, 421) * TAU);
    shards.add(shard);
  }
  scene.add(shards);
  const mist = makeParticles(THREE, mobile ? 140 : 340, { x: [-12, 12], y: [-0.4, 5], z: [-58, 4] }, abyss ? 0x7ef1e6 : 0xc8d6ff, 0.055, 0.18, 431);
  scene.add(mist.points);
  pack.particles.push(mist);

  const hazeTexture = makeRadialTexture(THREE, [
    [0, abyss ? "rgba(102,235,222,.2)" : "rgba(180,198,255,.18)"],
    [0.48, abyss ? "rgba(71,183,178,.08)" : "rgba(112,134,208,.07)"],
    [1, "rgba(30,45,76,0)"],
  ]);
  pack.textures.push(hazeTexture);
  const hazeMaterial = new THREE.SpriteMaterial({ map: hazeTexture, transparent: true, opacity: 0.72, depthWrite: false, blending: THREE.AdditiveBlending });
  const haze = new THREE.Group();
  for (let index = 0; index < (mobile ? 7 : 12); index += 1) {
    const veil = new THREE.Sprite(hazeMaterial);
    veil.position.set((seeded(index, 521) - 0.5) * 11, -0.15 + seeded(index, 523) * 1.8, -9 - index * 4.8);
    veil.scale.set(8 + seeded(index, 541) * 9, 2.2 + seeded(index, 547) * 2.8, 1);
    haze.add(veil);
  }
  scene.add(haze);

  const riverLight = new THREE.PointLight(abyss ? 0x65eadc : 0x829cff, 7, 28, 2);
  riverLight.position.set(0, 1.2, -13);
  scene.add(riverLight);
  const ruinFill = new THREE.DirectionalLight(abyss ? 0xa8fff3 : 0xc9d8ff, abyss ? 1.25 : 1.85);
  ruinFill.position.set(10, 11, 4);
  ruinFill.target.position.set(0, 1, -24);
  scene.add(ruinFill, ruinFill.target);
  const distantWarmth = new THREE.PointLight(fountain ? 0xffefc7 : 0xf2c99d, fountain ? 4 : 2.2, 34, 2);
  distantWarmth.position.set(-4, 5.5, -36);
  scene.add(distantWarmth);
  pack.update = (time, state, motion) => {
    riverMaterial.uniforms.time.value = time * (0.72 + state.elapsed * 0.18);
    riverMaterial.uniforms.motion.value = 0.42 + motion * 0.5;
    shards.rotation.y = Math.sin(time * 0.08) * 0.04 * motion;
    shards.children.forEach((shard, index) => {
      shard.rotation.y += 0.0015 * motion * (1 + index % 3);
      shard.position.y += Math.sin(time * 0.42 + index) * 0.0009 * motion;
    });
    shardMaterial.emissiveIntensity = 0.72 + state.elapsed * 0.72 + Math.sin(time * 0.7) * 0.08 * motion;
    riverLight.intensity = 5.5 + state.elapsed * 6;
    haze.position.x = Math.sin(time * 0.045) * 0.42 * motion;
    hazeMaterial.opacity = 0.58 + state.elapsed * 0.22;
    mist.points.position.z = ((time * 0.2 * motion) % 4) - 2;
    pack.sky.uniforms.starStrength.value = abyss ? 0 : 0.35 + state.elapsed * 0.42;
  };
  return pack;
}

function retagPack(THREE, pack, key, theme = {}) {
  pack.key = key;
  const originalUpdate = pack.update;
  const hemisphereIntensity = pack.hemisphere.intensity;
  const top = theme.top ? new THREE.Color(theme.top) : null;
  const horizon = theme.horizon ? new THREE.Color(theme.horizon) : null;
  const fog = theme.fog ? new THREE.Color(theme.fog) : null;
  if (theme.light) pack.keyLight.color.set(theme.light);
  pack.update = (time, state, motion) => {
    originalUpdate(time, state, motion);
    if (top) pack.sky.uniforms.topColor.value.copy(top);
    if (horizon) pack.sky.uniforms.horizonColor.value.copy(horizon);
    if (fog) pack.scene.fog.color.copy(fog);
    if (theme.exposure) pack.hemisphere.intensity = hemisphereIntensity * theme.exposure;
  };
  return pack;
}

const BUILDERS = {
  arbre_etoiles: buildStarTree,
  fontaine: (THREE, mobile, environment) => buildTimeRiver(THREE, mobile, environment, "fontaine"),
  eden: (THREE, mobile, environment) => retagPack(THREE, buildForest(THREE, mobile, environment), "eden", { top: 0x061714, horizon: 0x285b42, fog: 0x163b28, light: 0xfff0a6 }),
  fleuve_temps: (THREE, mobile, environment) => buildTimeRiver(THREE, mobile, environment, "fleuve_temps"),
  souvenirs: (THREE, mobile, environment) => retagPack(THREE, buildRainRefuge(THREE, mobile, environment), "souvenirs", { top: 0x15111d, horizon: 0x55445f, fog: 0x211827, light: 0xf0cba2 }),
  interstellaire: (THREE, mobile, environment) => buildCosmos(THREE, mobile, environment, "interstellaire"),
  galaxie: (THREE, mobile, environment) => buildCosmos(THREE, mobile, environment, "galaxie"),
  heaven: (THREE, mobile, environment) => retagPack(THREE, buildAurora(THREE, mobile, environment), "heaven", { top: 0x5d91ad, horizon: 0xb9ddeb, fog: 0x779eaf, light: 0xfff8d8, exposure: 1.22 }),
  oasis: (THREE, mobile, environment) => retagPack(THREE, buildSahara(THREE, mobile, environment), "oasis", { top: 0x171426, horizon: 0x8a573f, fog: 0x6b412b, light: 0xffd89b }),
  abysses: (THREE, mobile, environment) => buildTimeRiver(THREE, mobile, environment, "abysses"),
  refuge_pluie: buildRainRefuge,
  printemps: (THREE, mobile, environment) => retagPack(THREE, buildForest(THREE, mobile, environment), "printemps", { top: 0x8dc9d8, horizon: 0xd5e6cd, fog: 0x6c8e72, light: 0xfff3c3, exposure: 1.18 }),
  ete: (THREE, mobile, environment) => retagPack(THREE, buildSahara(THREE, mobile, environment), "ete", { top: 0x4e94c0, horizon: 0xf3c982, fog: 0xa6754c, light: 0xfff0ae, exposure: 1.12 }),
  automne: (THREE, mobile, environment) => retagPack(THREE, buildForest(THREE, mobile, environment), "automne", { top: 0x6b7280, horizon: 0xd49963, fog: 0x604232, light: 0xffd39d }),
  hiver: (THREE, mobile, environment) => retagPack(THREE, buildAurora(THREE, mobile, environment), "hiver", { top: 0x4c627a, horizon: 0xb4cad8, fog: 0x7893a1, light: 0xeef8ff, exposure: 1.1 }),
  pluie: (THREE, mobile, environment) => retagPack(THREE, buildRainRefuge(THREE, mobile, environment), "pluie", { top: 0x101923, horizon: 0x263748, fog: 0x17242e, light: 0xb7d5ea }),
  foret: buildForest,
  ocean: buildOcean,
  sahara: buildSahara,
  aurores: buildAurora,
  orage: (THREE, mobile, environment) => retagPack(THREE, buildOcean(THREE, mobile, environment), "orage", { top: 0x11131b, horizon: 0x333846, fog: 0x242a32, light: 0xdce8ff }),
  braises: (THREE, mobile, environment) => retagPack(THREE, buildRainRefuge(THREE, mobile, environment), "braises", { top: 0x120d0b, horizon: 0x271713, fog: 0x1a0e09, light: 0xffb36a }),
  aurore: (THREE, mobile, environment) => retagPack(THREE, buildAurora(THREE, mobile, environment), "aurore", { top: 0x02111d, horizon: 0x0d3448, fog: 0x14333d, light: 0xd9fff0 }),
  nuit: (THREE, mobile, environment) => retagPack(THREE, buildCosmos(THREE, mobile, environment, "interstellaire"), "nuit", { top: 0x030710, horizon: 0x10192a, fog: 0x080d16, light: 0xe8edff }),
};

function disposePack(pack) {
  pack.scene.traverse((node) => {
    node.geometry?.dispose?.();
    const materials = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
    for (const material of materials) material.dispose?.();
  });
  for (const texture of pack.textures) texture.dispose?.();
}

function setParticleDensity(pack, density, reducedMotion) {
  const ratios = [0, 0.26, 0.64, 1];
  const ratio = ratios[density] ?? ratios[2];
  for (const particle of pack.particles) {
    particle.points.geometry.setDrawRange(0, Math.round(particle.count * ratio));
    particle.material.opacity = particle.baseOpacity * (reducedMotion ? 0.74 : 1);
  }
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
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.18 : 1.55));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.98;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const environmentTarget = makeStudioEnvironment(THREE, renderer);
  const environmentTexture = environmentTarget.texture;
  const packs = new Map();
  let active = null;
  let width = 0;
  let height = 0;
  let frame = 0;
  let disposed = false;
  let firstFrame = false;
  let lastTime = 0;
  let pointerX = 0;
  let pointerY = 0;
  let targetPointerX = 0;
  let targetPointerY = 0;
  let lastDensity = -1;

  function resize() {
    const rect = stage.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width));
    const nextHeight = Math.max(1, Math.round(rect.height));
    if (width === nextWidth && height === nextHeight) return;
    width = nextWidth;
    height = nextHeight;
    renderer.setSize(width, height, false);
    for (const pack of packs.values()) {
      pack.camera.aspect = width / height;
      pack.camera.updateProjectionMatrix();
    }
  }

  function activate() {
    const key = app.dataset.ambience;
    if (!WORLD_KEYS.has(key)) {
      active = null;
      canvas.hidden = true;
      app.dataset.world3dActive = "false";
      if (fallbackCanvas) fallbackCanvas.style.opacity = "";
      return;
    }
    if (!packs.has(key)) {
      packs.set(key, BUILDERS[key](THREE, mobile, environmentTexture));
      width = 0;
    }
    active = packs.get(key);
    active.baseCameraX ??= active.camera.position.x;
    active.baseCameraY ??= active.camera.position.y;
    canvas.hidden = false;
    app.dataset.world3dActive = "true";
    lastDensity = -1;
    lastTime = 0;
  }

  function render(milliseconds) {
    if (disposed) return;
    if (!active || document.hidden) {
      frame = requestAnimationFrame(render);
      return;
    }
    if (milliseconds - lastTime < (mobile ? 28 : 14)) {
      frame = requestAnimationFrame(render);
      return;
    }
    const delta = Math.min(0.04, (milliseconds - lastTime) / 1000 || 0.016);
    lastTime = milliseconds;
    const time = milliseconds / 1000;
    resize();
    const state = sessionState(app);
    const motion = reducedMotion ? 0 : [0, 0.28, 0.66, 1][state.density];
    if (state.density !== lastDensity) {
      setParticleDensity(active, state.density, reducedMotion);
      lastDensity = state.density;
    }
    active.update(time, state, motion);

    pointerX += (targetPointerX - pointerX) * Math.min(1, delta * 2.1);
    pointerY += (targetPointerY - pointerY) * Math.min(1, delta * 2.1);
    active.camera.position.x = active.baseCameraX + pointerX * (reducedMotion ? 0 : 0.72);
    active.camera.position.y += (active.baseCameraY - pointerY * 0.24 - active.camera.position.y) * Math.min(1, delta * 0.5);
    active.camera.lookAt(active.target);
    renderer.render(active.scene, active.camera);

    if (!firstFrame) {
      firstFrame = true;
      app.dataset.world3d = "ready";
    }
    if (fallbackCanvas) fallbackCanvas.style.opacity = "0";
    frame = requestAnimationFrame(render);
  }

  const mutationObserver = new MutationObserver(activate);
  mutationObserver.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
  const resizeObserver = new ResizeObserver(() => { width = 0; });
  resizeObserver.observe(stage);
  const pointerMove = (event) => {
    const rect = stage.getBoundingClientRect();
    targetPointerX = clamp((event.clientX - rect.left) / rect.width, 0, 1) * 2 - 1;
    targetPointerY = clamp((event.clientY - rect.top) / rect.height, 0, 1) * 2 - 1;
  };
  const pointerLeave = () => {
    targetPointerX = 0;
    targetPointerY = 0;
  };
  stage.addEventListener("pointermove", pointerMove, { passive: true });
  stage.addEventListener("pointerleave", pointerLeave, { passive: true });

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    active = null;
    canvas.hidden = true;
    app.dataset.world3d = "fallback";
    app.dataset.world3dActive = "false";
    app.dataset.world3dReason = "context-lost";
    if (fallbackCanvas) fallbackCanvas.style.opacity = "";
  }, { once: true });

  window.addEventListener("pagehide", () => {
    disposed = true;
    cancelAnimationFrame(frame);
    mutationObserver.disconnect();
    resizeObserver.disconnect();
    stage.removeEventListener("pointermove", pointerMove);
    stage.removeEventListener("pointerleave", pointerLeave);
    for (const pack of packs.values()) disposePack(pack);
    environmentTarget.dispose();
    renderer.dispose();
  }, { once: true });

  activate();
  frame = requestAnimationFrame(render);
}

async function boot() {
  const app = document.querySelector("#focus-app");
  const stage = document.querySelector("#focus-stage");
  const fallback = document.querySelector("#decor-canvas");
  if (!app || !stage || !fallback) return;

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
    if (WORLD_KEYS.has(app.dataset.ambience)) {
      start().catch((error) => console.error("Univers 3D indisponible", error));
    }
  };

  if (WORLD_KEYS.has(app.dataset.ambience)) {
    await start();
  } else {
    observer = new MutationObserver(maybeStart);
    observer.observe(app, { attributes: true, attributeFilter: ["data-ambience"] });
    window.addEventListener("pagehide", () => observer?.disconnect(), { once: true });
  }
}

boot().catch((error) => console.error("Univers 3D indisponible", error));
