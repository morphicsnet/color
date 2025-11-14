export type OKLab = { L: number; a: number; b: number };
export type OKLCh = { L: number; C: number; h: number };
export type MixInput = { id: string; color: OKLab; weight: number };
export type MixPolicy = "normalize" | "strict_sum_1";
