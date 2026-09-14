export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];

export interface JsonObject {
  [key: string]: JsonValue | undefined;
}

export type BioinformaticsDisplayComponent =
  | "citation"
  | "dataset"
  | "compound"
  | "protein"
  | "protein_structure"
  | "protein_network"
  | "pathway"
  | "ontology_term"
  | "gene"
  | "genomic_feature"
  | "variant"
  | "taxonomy"
  | "identifier_conversion"
  | "database"
  | "linkset"
  | "project"
  | "sample"
  | "run"
  | "download_plan"
  | "sample_sheet"
  | "runtime_status"
  | (string & {});

export type BioinformaticsLinkKind =
  | "external"
  | "download"
  | "related"
  | (string & {});

export type BioinformaticsPreviewKind =
  | "sequence"
  | "feature_track"
  | "structure_3d"
  | "chemical_structure"
  | "network"
  | "survival_curve"
  | "heatmap_matrix"
  | "citation_list"
  | "xref_groups"
  | "download_manifest"
  | "table"
  | "text"
  | (string & {});

export interface BioinformaticsResultEnvelope {
  schema_version?: string;
  provenance?: BioinformaticsProvenance;
  source?: BioinformaticsProvenance;
  database?: string;
  query?: string | null;
  returned?: number;
  records?: BioinformaticsRecord[];
  citations?: BioinformaticsCitation[];
  [key: string]: unknown;
}

export interface BioinformaticsDynamicContextResult {
  schema_version: string;
  context_schema_version: "bioinformatics.dynamic_context.v1" | (string & {});
  database: string;
  operation: "resolve_context";
  query?: Record<string, unknown>;
  returned: number;
  total: number;
  contexts: BioinformaticsDynamicContext[];
  entities?: BioinformaticsDynamicContextSummary[];
  recommended_calls?: BioinformaticsRecommendedCall[];
  source?: BioinformaticsProvenance;
  provenance?: BioinformaticsProvenance;
  sources?: BioinformaticsProvenance[];
  diagnostics?: BioinformaticsDiagnostic[];
  raw?: unknown;
  [key: string]: unknown;
}

export interface BioinformaticsProvenance {
  endpoint?: string;
  params?: Record<string, unknown>;
  retrieved_at?: string;
  [key: string]: unknown;
}

export interface BioinformaticsDynamicContext {
  kind?: string;
  group?: string;
  parameter_name: string;
  value: unknown;
  label: string;
  title?: string;
  description?: string;
  url?: string;
  source?: string;
  metadata?: Record<string, unknown>;
  display?: BioinformaticsDynamicContextDisplay;
  [key: string]: unknown;
}

export interface BioinformaticsDynamicContextDisplay {
  component?: BioinformaticsDisplayComponent;
  chip_label?: string;
  icon?: string;
  title?: string;
  subtitle?: string;
  description?: string;
  metadata?: BioinformaticsDisplayField[];
  badges?: BioinformaticsBadge[];
  actions?: BioinformaticsAction[];
  hover?: BioinformaticsHover;
  primary_url?: string;
  [key: string]: unknown;
}

export interface BioinformaticsDynamicContextSummary {
  parameter_name?: string;
  value?: unknown;
  label?: string;
  kind?: string;
  url?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BioinformaticsRecommendedCall {
  server?: string;
  tool_name: string;
  arguments?: Record<string, unknown>;
  reason?: string;
  missing_arguments?: string[];
  [key: string]: unknown;
}

export interface BioinformaticsDiagnostic {
  code?: string;
  severity?: "info" | "warning" | "error" | (string & {});
  message: string;
  recoverable?: boolean;
  suggested_action?: string;
  details?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BioinformaticsRecord {
  schema_version: string;
  type: string;
  record_type: string;
  database: string;
  entrez_database?: string;
  id: string;
  uid?: string;
  stable_id: string;
  label: string;
  title: string;
  description?: string;
  url: string;
  icon: string;
  identifiers?: Record<
    string,
    BioinformaticsIdentifier | BioinformaticsIdentifier[]
  >;
  links?: BioinformaticsAction[];
  display: BioinformaticsRecordDisplay;
  citation?: BioinformaticsCitation;
  related?: Record<string, unknown>;
  data?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BioinformaticsRecordDisplay {
  component: BioinformaticsDisplayComponent;
  chip_label: string;
  icon: string;
  title: string;
  subtitle?: string;
  description?: string;
  metadata: BioinformaticsDisplayField[];
  badges: BioinformaticsBadge[];
  actions: BioinformaticsAction[];
  hover: BioinformaticsHover;
  primary_url?: string;
  sections?: BioinformaticsDisplaySection[];
  previews?: BioinformaticsPreview[];
  [key: string]: unknown;
}

export interface BioinformaticsDisplayField {
  label: string;
  value: string | number | boolean;
  [key: string]: unknown;
}

export interface BioinformaticsBadge {
  label: string;
  kind: string;
  [key: string]: unknown;
}

export interface BioinformaticsAction {
  label: string;
  url: string;
  kind?: BioinformaticsLinkKind;
  primary?: boolean;
  [key: string]: unknown;
}

export interface BioinformaticsIdentifier {
  namespace: string;
  id: string;
  label: string;
  url?: string;
  [key: string]: unknown;
}

export interface BioinformaticsHover {
  title: string;
  subtitle?: string;
  icon?: string;
  fields: BioinformaticsDisplayField[];
  [key: string]: unknown;
}

export interface BioinformaticsDisplaySection {
  key: string;
  title: string;
  kind?: string;
  fields?: BioinformaticsDisplayField[];
  rows?: Record<string, unknown>[];
  items?: unknown[];
  groups?: unknown[];
  tracks?: unknown[];
  summary?: Record<string, unknown>;
  text?: string;
  [key: string]: unknown;
}

export interface BioinformaticsPreview {
  kind: BioinformaticsPreviewKind;
  title: string;
  provider?: string;
  id?: string;
  url?: string;
  format?: string;
  mime_type?: string;
  length?: number | string;
  primary?: boolean;
  section_key?: string;
  actions?: BioinformaticsAction[];
  data?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BioinformaticsCitation {
  schema_version: string;
  type: "citation" | (string & {});
  citation_type: "article" | (string & {});
  database: string;
  id: string;
  stable_id: string;
  label: string;
  title: string;
  authors?: string[];
  first_author?: string | null;
  journal?: string;
  journal_abbreviation?: string;
  publication_date?: string;
  doi?: string | null;
  pmcid?: string | null;
  url: string;
  icon?: string;
  summary?: string;
  hover: BioinformaticsHover;
  tooltip?: BioinformaticsHover;
  links?: BioinformaticsAction[];
  [key: string]: unknown;
}

export function getBioinformaticsRecords(
  payload: BioinformaticsResultEnvelope | unknown,
): BioinformaticsRecord[] {
  if (!isObject(payload) || !Array.isArray(payload.records)) {
    return [];
  }
  return payload.records.filter(isBioinformaticsRecord);
}

export function isBioinformaticsDynamicContextResult(
  payload: unknown,
): payload is BioinformaticsDynamicContextResult {
  return (
    isObject(payload) &&
    payload.context_schema_version === "bioinformatics.dynamic_context.v1" &&
    payload.operation === "resolve_context" &&
    Array.isArray(payload.contexts)
  );
}

export function getBioinformaticsDynamicContexts(
  payload: BioinformaticsDynamicContextResult | unknown,
): BioinformaticsDynamicContext[] {
  if (!isBioinformaticsDynamicContextResult(payload)) {
    return [];
  }
  return payload.contexts.filter(isBioinformaticsDynamicContext);
}

export function getDynamicContextEntities(
  payload: BioinformaticsDynamicContextResult | unknown,
): BioinformaticsDynamicContextSummary[] {
  if (!isObject(payload) || !Array.isArray(payload.entities)) {
    return [];
  }
  return payload.entities.filter(isDynamicContextSummary);
}

export function getDynamicContextRecommendedCalls(
  payload: BioinformaticsDynamicContextResult | unknown,
): BioinformaticsRecommendedCall[] {
  if (!isObject(payload) || !Array.isArray(payload.recommended_calls)) {
    return [];
  }
  return payload.recommended_calls.filter(isRecommendedCall);
}

export function getDynamicContextPrimaryUrl(
  context: BioinformaticsDynamicContext,
): string | undefined {
  const display = isObject(context.display) ? context.display : undefined;
  if (display) {
    const primaryUrl = cleanUrl(display.primary_url);
    if (primaryUrl) {
      return primaryUrl;
    }
  }
  const contextUrl = cleanUrl(context.url);
  if (contextUrl) {
    return contextUrl;
  }
  const actions = Array.isArray(display?.actions) ? display.actions : [];
  for (const action of actions) {
    if (isObject(action)) {
      const actionUrl = cleanUrl(action.url);
      if (actionUrl) {
        return actionUrl;
      }
    }
  }
  return undefined;
}

export function getDynamicContextHover(
  context: BioinformaticsDynamicContext,
): BioinformaticsHover {
  const display = isObject(context.display) ? context.display : undefined;
  const hover = isObject(display?.hover) ? display?.hover : undefined;
  if (
    hover &&
    typeof hover.title === "string" &&
    Array.isArray(hover.fields)
  ) {
    return hover as unknown as BioinformaticsHover;
  }
  return {
    title: displayString(context.title ?? context.label ?? context.value ?? context.parameter_name),
    subtitle: displayString(context.description),
    icon: displayString(display?.icon ?? context.kind),
    fields: [],
  };
}

export function getRecordPrimaryUrl(
  record: BioinformaticsRecord,
): string | undefined {
  return (
    cleanUrl(record.display?.primary_url) ??
    cleanUrl(record.url) ??
    record.display?.actions?.map((action) => action.url).find(Boolean) ??
    record.links?.map((link) => link.url).find(Boolean)
  );
}

export function getRecordActions(
  record: BioinformaticsRecord,
): BioinformaticsAction[] {
  if (record.display?.actions?.length) {
    return record.display.actions;
  }
  return record.links ?? [];
}

export function getRecordHover(record: BioinformaticsRecord): BioinformaticsHover {
  return record.display?.hover ?? {
    title: record.title || record.label || record.stable_id,
    subtitle: record.description,
    icon: record.icon,
    fields: [],
  };
}

export function isSafeExternalUrl(url: string | undefined): url is string {
  return typeof url === "string" && /^https?:\/\//i.test(url);
}

function isBioinformaticsRecord(value: unknown): value is BioinformaticsRecord {
  return (
    isObject(value) &&
    typeof value.schema_version === "string" &&
    typeof value.record_type === "string" &&
    typeof value.database === "string" &&
    typeof value.stable_id === "string" &&
    isObject(value.display) &&
    typeof value.display.component === "string"
  );
}

function isBioinformaticsDynamicContext(
  value: unknown,
): value is BioinformaticsDynamicContext {
  return (
    isObject(value) &&
    typeof value.parameter_name === "string" &&
    "value" in value &&
    typeof value.label === "string"
  );
}

function isDynamicContextSummary(
  value: unknown,
): value is BioinformaticsDynamicContextSummary {
  return isObject(value) && ("value" in value || "parameter_name" in value);
}

function isRecommendedCall(value: unknown): value is BioinformaticsRecommendedCall {
  return isObject(value) && typeof value.tool_name === "string";
}

function cleanUrl(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function displayString(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
