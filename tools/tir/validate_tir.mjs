#!/usr/bin/env node
/**
 * validate_tir.mjs
 *
 * Validate T-IR JSON documents against docs/ir/tir-schema.json using Ajv 2020.
 *
 * Usage:
 *   node tools/tir/validate_tir.mjs [--schema docs/ir/tir-schema.json] [--examples] [files...]
 *   node tools/tir/validate_tir.mjs --stdin
 *
 * Exit codes:
 *   0: all documents valid
 *   1: one or more documents invalid
 *   2: setup error (schema not found, Ajv missing, or invalid input)
 *
 * Requires:
 *   npm i ajv
 */
import fs from "fs";
import path from "path";
import process from "process";
import { fileURLToPath } from "url";
import Ajv2020 from "ajv/dist/2020.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_SCHEMA = "docs/ir/tir-schema.json";

function printUsage() {
  console.error(`Usage:
  node tools/tir/validate_tir.mjs [--schema ${DEFAULT_SCHEMA}] [--examples] [files...]
  node tools/tir/validate_tir.mjs --stdin
Options:
  --schema <path>   Path to T-IR JSON schema (default: ${DEFAULT_SCHEMA})
  --examples        Validate all JSON files under docs/ir/examples/
  --stdin           Read a single JSON document from stdin
  --verbose         Print [ok] lines for valid documents`);
}

function parseArgs(argv) {
  const args = {
    schema: DEFAULT_SCHEMA,
    examples: false,
    stdin: false,
    verbose: false,
    files: [],
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--schema") {
      if (i + 1 >= argv.length) {
        throw new Error("--schema requires a path");
      }
      args.schema = argv[++i];
    } else if (a === "--examples") {
      args.examples = true;
    } else if (a === "--stdin") {
      args.stdin = true;
    } else if (a === "--verbose") {
      args.verbose = true;
    } else if (a === "--help" || a === "-h") {
      args.help = true;
    } else if (a.startsWith("-")) {
      throw new Error(`Unknown option: ${a}`);
    } else {
      args.files.push(a);
    }
  }
  return args;
}

function fileExists(p) {
  try {
    fs.accessSync(p, fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

function loadJsonFromFile(p) {
  const buf = fs.readFileSync(p, "utf-8");
  return JSON.parse(buf);
}

async function loadJsonFromStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.from(chunk));
  }
  const buf = Buffer.concat(chunks).toString("utf-8");
  return JSON.parse(buf);
}

function discoverExampleFiles() {
  const base = "docs/ir/examples";
  if (!fileExists(base)) return [];
  const entries = fs.readdirSync(base, { withFileTypes: true });
  const files = [];
  for (const e of entries) {
    if (e.isFile() && e.name.endsWith(".json")) {
      files.push(path.join(base, e.name));
    }
  }
  files.sort();
  return files;
}

function formatAjvError(err) {
  // Ajv v8 error shape: { instancePath, message, keyword, params, schemaPath }
  const ptr = err.instancePath || "";
  const where = ptr ? `$${ptr}` : "$";
  return `${where}: ${err.message}`;
}

function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (e) {
    console.error(`ERROR: ${e.message}`);
    printUsage();
    return 2;
  }
  if (args.help) {
    printUsage();
    return 0;
  }

  const schemaPath = args.schema;
  if (!fileExists(schemaPath)) {
    console.error(`ERROR: schema not found: ${schemaPath}`);
    return 2;
  }

  let schema;
  try {
    schema = loadJsonFromFile(schemaPath);
  } catch (e) {
    console.error(`ERROR: failed to read schema '${schemaPath}': ${e.message}`);
    return 2;
  }

  let ajv;
  try {
    ajv = new Ajv2020({
      allErrors: true,
      strict: false,
      allowUnionTypes: true,
    });
  } catch (e) {
    console.error(`ERROR: failed to initialize Ajv: ${e.message}`);
    return 2;
  }

  let validate;
  try {
    validate = ajv.compile(schema);
  } catch (e) {
    console.error(`ERROR: failed to compile schema: ${e.message}`);
    return 2;
  }

  const targets = [];

  if (args.stdin) {
    try {
      const data = fs.existsSync(0) ? fs.readFileSync(0, "utf-8") : null; // best effort
      if (data === null || data === undefined || data.length === 0) {
        // Fallback to async if sync read failed
        // eslint-disable-next-line no-async-promise-executor
        return (async () => {
          try {
            const j = await loadJsonFromStdin();
            targets.push(["stdin", j]);
            const code = runValidation(validate, targets, args.verbose);
            process.exit(code);
          } catch (e) {
            console.error(`ERROR: failed to read JSON from stdin: ${e.message}`);
            process.exit(2);
          }
        })();
      } else {
        targets.push(["stdin", JSON.parse(data)]);
      }
    } catch (e) {
      console.error(`ERROR: failed to read JSON from stdin: ${e.message}`);
      return 2;
    }
  }

  let files = [];
  if (args.examples) {
    files = files.concat(discoverExampleFiles());
  }
  if (args.files && args.files.length > 0) {
    files = files.concat(args.files);
  }

  if (targets.length === 0 && files.length === 0) {
    // Default to examples if present, otherwise print usage hint.
    const ex = discoverExampleFiles();
    if (ex.length > 0) {
      files = ex;
    } else {
      printUsage();
      console.error("No input specified. Provide files, --examples, or --stdin.");
      return 2;
    }
  }

  for (const p of files) {
    try {
      const data = loadJsonFromFile(p);
      targets.push([p, data]);
    } catch (e) {
      console.error(`[fail] ${p}: failed to parse JSON: ${e.message}`);
      return 2;
    }
  }

  return runValidation(validate, targets, args.verbose);
}

function runValidation(validate, targets, verbose) {
  let anyFail = false;
  for (const [name, data] of targets) {
    const ok = validate(data);
    if (!ok) {
      anyFail = true;
      const errors = validate.errors || [];
      console.error(`[fail] ${name}: ${errors.length} error(s):`);
      errors.forEach((err, i) => {
        console.error(`  ${String(i + 1).padStart(3, "0")}) ${formatAjvError(err)}`);
      });
    } else if (verbose) {
      console.log(`[ok] ${name}`);
    }
  }

  if (anyFail) return 1;
  console.log("[ok] All T-IR documents valid");
  return 0;
}

const code = main();
if (typeof code === "number") {
  process.exit(code);
}