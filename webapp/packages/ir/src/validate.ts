import Ajv from "ajv";
import type { IRDocument } from "./ir";

// NOTE: In browser, the schema will be loaded via fetch; for tests, we can inject schema JSON.
export function validateIR(doc: IRDocument, schema: object): { valid: boolean; errors?: string[] } {
  const ajv = new Ajv({ allErrors: true, strict: false });
  const validate = ajv.compile(schema);
  const valid = validate(doc) as boolean;
  return { valid, errors: (validate.errors || []).map((e) => ajv.errorsText([e])) };
}
