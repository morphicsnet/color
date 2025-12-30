/**
 * OKLab space implementation for TypeScript.
 */

import type { OKLab } from '@oklab/core';
import type { Space, GroundRegion } from './space';

// OKLab space implementation
export class OKLabSpace implements Space<OKLab> {
  distance(a: OKLab, b: OKLab): number {
    const dl = a.L - b.L;
    const da = a.a - b.a;
    const db = a.b - b.b;
    return Math.sqrt(dl * dl + da * da + db * db);
  }

  mix(points: OKLab[], weights: number[]): OKLab {
    if (points.length === 0) {
      throw new Error('Cannot mix empty list of points');
    }
    if (points.length !== weights.length) {
      throw new Error('Points and weights must have same length');
    }

    // Normalize weights
    const totalWeight = weights.reduce((sum, w) => sum + w, 0);
    const normalizedWeights = totalWeight === 0
      ? weights.map(() => 1 / points.length)
      : weights.map(w => w / totalWeight);

    // Mix in OKLab space
    const mixedL = points.reduce((sum, p, i) => sum + p.L * normalizedWeights[i], 0);
    const mixedA = points.reduce((sum, p, i) => sum + p.a * normalizedWeights[i], 0);
    const mixedB = points.reduce((sum, p, i) => sum + p.b * normalizedWeights[i], 0);

    return { L: mixedL, a: mixedA, b: mixedB };
  }

  validate(point: OKLab): boolean {
    // OKLab has L in [0,1], a,b typically in [-1,1] but can be wider
    return point.L >= 0 && point.L <= 1 &&
           point.a >= -1 && point.a <= 1 &&
           point.b >= -1 && point.b <= 1;
  }
}

// Spherical region around a center point
export class SphericalRegion implements GroundRegion<OKLab> {
  constructor(
    public center: OKLab,
    public radius: number,
    private space: OKLabSpace
  ) {}

  contains(point: OKLab): boolean {
    return this.space.distance(this.center, point) <= this.radius;
  }
}

// Utility for creating color regions
export function createColorRegion(colorName: string, space: OKLabSpace): SphericalRegion {
  // Simplified color mapping - in practice would use OKLab values for actual colors
  const colorMap: Record<string, OKLab> = {
    "red": { L: 0.5, a: 0.3, b: 0.2 },
    "blue": { L: 0.4, a: -0.1, b: -0.3 },
    "green": { L: 0.6, a: -0.2, b: 0.2 },
    "yellow": { L: 0.8, a: 0.1, b: 0.2 },
    "purple": { L: 0.4, a: 0.1, b: -0.2 }
  };

  const center = colorMap[colorName.toLowerCase()] || { L: 0.5, a: 0, b: 0 };
  return new SphericalRegion(center, 0.1, space);
}