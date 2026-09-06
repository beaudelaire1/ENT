// Bruit procédural du Sablier.
//
// Aucune texture n'est téléchargée : tout le grain des matières — sable, cire, nacre,
// métal brossé, roche, régolithe — est calculé ici puis gravé dans un canvas. C'est ce
// qui sépare un objet rendu d'une icône agrandie : une surface sans micro-relief renvoie
// la lumière de façon uniforme et se lit immédiatement comme un aplat.

const PERM = (() => {
  // Permutation déterministe : le même monde doit se redessiner à l'identique d'une
  // session à l'autre, sinon la scène « clignote » à chaque rechargement.
  const table = new Uint8Array(512);
  let seed = 1975;
  for (let i = 0; i < 256; i += 1) table[i] = i;
  for (let i = 255; i > 0; i -= 1) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    const j = seed % (i + 1);
    const swap = table[i];
    table[i] = table[j];
    table[j] = swap;
  }
  for (let i = 0; i < 256; i += 1) table[i + 256] = table[i];
  return table;
})();

const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);
const lerp = (a, b, t) => a + (b - a) * t;

function gradient(hash, x, y) {
  switch (hash & 7) {
    case 0: return x + y;
    case 1: return x - y;
    case 2: return -x + y;
    case 3: return -x - y;
    case 4: return x;
    case 5: return -x;
    case 6: return y;
    default: return -y;
  }
}

// Bruit de Perlin 2D, dans [-1, 1].
export function perlin(x, y) {
  const xi = Math.floor(x) & 255, yi = Math.floor(y) & 255;
  const xf = x - Math.floor(x), yf = y - Math.floor(y);
  const u = fade(xf), v = fade(yf);
  const aa = PERM[PERM[xi] + yi], ab = PERM[PERM[xi] + yi + 1];
  const ba = PERM[PERM[xi + 1] + yi], bb = PERM[PERM[xi + 1] + yi + 1];
  return lerp(
    lerp(gradient(aa, xf, yf), gradient(ba, xf - 1, yf), u),
    lerp(gradient(ab, xf, yf - 1), gradient(bb, xf - 1, yf - 1), u),
    v,
  );
}

// Somme d'octaves : le relief fin se superpose au relief large, comme dans la nature.
export function fbm(x, y, octaves = 5, lacunarity = 2.03, gain = 0.5) {
  let sum = 0, amplitude = 1, frequency = 1, norm = 0;
  for (let i = 0; i < octaves; i += 1) {
    sum += perlin(x * frequency, y * frequency) * amplitude;
    norm += amplitude;
    amplitude *= gain;
    frequency *= lacunarity;
  }
  return sum / norm;
}

// Bruit à crêtes : donne les arêtes des dunes et des massifs, là où le fbm simple
// n'offre que des bosses molles.
export function ridged(x, y, octaves = 5, lacunarity = 2.07, gain = 0.5) {
  let sum = 0, amplitude = 1, frequency = 1, norm = 0;
  for (let i = 0; i < octaves; i += 1) {
    const value = 1 - Math.abs(perlin(x * frequency, y * frequency));
    sum += value * value * amplitude;
    norm += amplitude;
    amplitude *= gain;
    frequency *= lacunarity;
  }
  return sum / norm;
}

// Bruit cellulaire : distance au point le plus proche d'une grille perturbée. C'est lui
// qui donne les grains de sable, les écailles de roche et les cratères.
export function worley(x, y, jitter = 1) {
  const xi = Math.floor(x), yi = Math.floor(y);
  let best = 8;
  for (let dy = -1; dy <= 1; dy += 1) {
    for (let dx = -1; dx <= 1; dx += 1) {
      const cx = xi + dx, cy = yi + dy;
      const hash = PERM[(PERM[cx & 255] + (cy & 255)) & 511];
      const ox = ((hash & 15) / 15 - 0.5) * jitter + 0.5;
      const oy = ((hash >> 4) / 15 - 0.5) * jitter + 0.5;
      const px = cx + ox - x, py = cy + oy - y;
      const distance = px * px + py * py;
      if (distance < best) best = distance;
    }
  }
  return Math.min(1, Math.sqrt(best));
}

// Canvas hors écran : `size` pixels de côté, remplis par `paint(imageData, size)`.
export function surface(size, paint) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const image = context.createImageData(size, size);
  paint(image.data, size);
  context.putImageData(image, 0, 0);
  return canvas;
}

// Carte de hauteur en niveaux de gris, à partir d'une fonction continue.
export function heightField(size, height) {
  const field = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) field[y * size + x] = height(x / size, y / size);
  }
  return field;
}

// Conversion relief → carte de normales (opérateur de Sobel). Le champ est bouclé sur
// lui-même : les textures se répètent sans couture visible sur les grandes surfaces.
export function normalMap(field, size, strength = 2.4) {
  return surface(size, (data) => {
    const at = (x, y) => field[((y + size) % size) * size + ((x + size) % size)];
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        const dx = (at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1))
          - (at(x - 1, y - 1) + 2 * at(x - 1, y) + at(x - 1, y + 1));
        const dy = (at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1))
          - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1));
        let nx = -dx * strength, ny = -dy * strength, nz = 1;
        const length = Math.hypot(nx, ny, nz) || 1;
        nx /= length; ny /= length; nz /= length;
        const index = (y * size + x) * 4;
        data[index] = (nx * 0.5 + 0.5) * 255;
        data[index + 1] = (ny * 0.5 + 0.5) * 255;
        data[index + 2] = (nz * 0.5 + 0.5) * 255;
        data[index + 3] = 255;
      }
    }
  });
}

// Carte en niveaux de gris (rugosité, occlusion, épaisseur…) depuis un champ.
export function grayscale(field, size, low = 0, high = 1) {
  return surface(size, (data) => {
    for (let i = 0; i < size * size; i += 1) {
      const value = Math.max(0, Math.min(1, low + field[i] * (high - low)));
      const channel = value * 255;
      data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = channel;
      data[i * 4 + 3] = 255;
    }
  });
}
