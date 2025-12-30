/**
 * Core abstractions for symbol grounding framework.
 *
 * Extracted from Coq formal specifications in coq/Color/Core.v
 */

import type { OKLab } from '@oklab/core';

// Type for symbols (string identifiers)
export type Symbol = string;

/**
 * Abstract ground space for symbol grounding.
 *
 * Corresponds to Coq Record GroundSpace with carrier, distance, mix, validate.
 */
export interface Space<S> {
  /** Distance metric between points in the space */
  distance(a: S, b: S): number;

  /** Convex combination of points with weights */
  mix(points: S[], weights: number[]): S;

  /** Check if point is valid in this space */
  validate(point: S): boolean;
}

/**
 * Abstract geometric region in a ground space.
 *
 * Corresponds to Coq Record GroundRegion with contains predicate.
 */
export interface GroundRegion<S> {
  /** Check if point is contained in this region */
  contains(point: S): boolean;
}

/**
 * Mapping from symbols to regions in a ground space.
 *
 * Corresponds to Coq Record Grounding with regions function.
 */
export class Grounding<S> {
  private regions = new Map<Symbol, GroundRegion<S>>();

  constructor(private space: Space<S>) {}

  /** Bind a symbol to a region in the space */
  bindRegion(symbol: Symbol, region: GroundRegion<S>): void {
    this.regions.set(symbol, region);
  }

  /** Get the region for a symbol */
  getRegion(symbol: Symbol): GroundRegion<S> {
    const region = this.regions.get(symbol);
    if (!region) {
      throw new Error(`No region bound for symbol: ${symbol}`);
    }
    return region;
  }

  /** Find the symbol whose region is closest to the point */
  nearestSymbol(point: S): Symbol | null {
    let minDistance = Infinity;
    let nearest: Symbol | null = null;

    for (const [symbol, region] of this.regions) {
      // Check if point is in region
      if (region.contains(point)) {
        return symbol;
      }

      // Fallback: find closest region center (requires region to have center)
      try {
        const center = (region as any).center as S;
        if (center) {
          const distance = this.space.distance(point, center);
          if (distance < minDistance) {
            minDistance = distance;
            nearest = symbol;
          }
        }
      } catch {
        // Region doesn't have center, skip
      }
    }

    return nearest;
  }

  /** Calculate similarity between two symbols' regions */
  similarity(symbol1: Symbol, symbol2: Symbol): number {
    const region1 = this.getRegion(symbol1);
    const region2 = this.getRegion(symbol2);

    // Placeholder implementation
    // In practice, would compute region overlap or distance
    try {
      const center1 = (region1 as any).center as S;
      const center2 = (region2 as any).center as S;
      if (center1 && center2) {
        return 1.0 / (1.0 + this.space.distance(center1, center2));
      }
    } catch {
      // No center information available
    }

    return 0.0;
  }
}