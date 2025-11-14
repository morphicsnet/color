export interface IRDocument {
  ir_version: string;
  document: unknown;
  sections: unknown[];
  statements: unknown[];
  symbols: unknown[];
  typesystem?: unknown;
  geometry_domain?: GeometryDomain;
  dependency_graph?: unknown;
  build_meta?: unknown;
}

export interface GeometryDomain {
  color_models?: unknown;
  transforms?: unknown[];
  metrics?: unknown[];
}
