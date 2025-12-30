/**
 * Tests for grounding space functionality.
 */

import { describe, it, expect } from 'vitest';
import { OKLabSpace, SphericalRegion, Grounding } from './index';

describe('OKLabSpace', () => {
  const space = new OKLabSpace();

  it('should calculate distance correctly', () => {
    const c1 = { L: 0.5, a: 0.1, b: 0.2 };
    const c2 = { L: 0.6, a: -0.1, b: 0.1 };

    const distance = space.distance(c1, c2);
    expect(distance).toBeGreaterThan(0);
    expect(distance).toBe(space.distance(c2, c1)); // symmetric
  });

  it('should mix colors correctly', () => {
    const c1 = { L: 0.4, a: 0.0, b: 0.0 };
    const c2 = { L: 0.6, a: 0.0, b: 0.0 };
    const weights = [0.5, 0.5];

    const result = space.mix([c1, c2], weights);
    expect(result.L).toBeCloseTo(0.5, 5);
    expect(result.a).toBeCloseTo(0.0, 5);
    expect(result.b).toBeCloseTo(0.0, 5);
  });

  it('should validate OKLab colors', () => {
    const validColor = { L: 0.5, a: 0.1, b: 0.2 };
    const invalidColor = { L: 1.5, a: 0.1, b: 0.2 }; // L > 1

    expect(space.validate(validColor)).toBe(true);
    expect(space.validate(invalidColor)).toBe(false);
  });
});

describe('Grounding', () => {
  const space = new OKLabSpace();
  const grounding = new Grounding(space);

  it('should bind and retrieve regions', () => {
    const region = new SphericalRegion(
      { L: 0.5, a: 0.1, b: 0.2 },
      0.1,
      space
    );

    grounding.bindRegion('test', region);
    const retrieved = grounding.getRegion('test');

    expect(retrieved).toBe(region);
  });

  it('should find nearest symbol', () => {
    const region = new SphericalRegion(
      { L: 0.5, a: 0.1, b: 0.2 },
      0.1,
      space
    );

    grounding.bindRegion('target', region);

    // Point inside region
    const result = grounding.nearestSymbol({ L: 0.5, a: 0.1, b: 0.2 });
    expect(result).toBe('target');
  });

  it('should calculate similarity', () => {
    const r1 = new SphericalRegion({ L: 0.5, a: 0.1, b: 0.2 }, 0.1, space);
    const r2 = new SphericalRegion({ L: 0.6, a: -0.1, b: 0.1 }, 0.1, space);

    grounding.bindRegion('color1', r1);
    grounding.bindRegion('color2', r2);

    const similarity = grounding.similarity('color1', 'color2');
    expect(similarity).toBeGreaterThan(0);
    expect(similarity).toBeLessThan(1);
  });
});