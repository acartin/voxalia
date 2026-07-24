import type React from "react";

export type CrudChoice = {
  value: string;
  label: string;
};

export type CrudField = {
  name: string;
  label: string;
  type?: "email" | "password" | "tel" | "text";
  required?: boolean;
  minLength?: number;
  placeholder?: string;
  helperText?: string;
  defaultValue?: string;
  sourceName?: string;
  editable?: boolean;
  createOnly?: boolean;
  editOnly?: boolean;
  control?: "input" | "select" | "checkbox-group";
  options?: CrudChoice[];
  optionsSource?: string;
};

export type CrudColumn<TRecord extends Record<string, unknown>> = {
  id: string;
  header: string;
  cell?: (record: TRecord) => React.ReactNode;
  searchValue?: (record: TRecord) => string;
  sortValue?: (record: TRecord) => unknown;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
};

export type CrudAction = "view" | "edit" | "deactivate" | "workspace";

export type CrudResourceConfig<TRecord extends Record<string, unknown>> = {
  id: string;
  title: string;
  description: string;
  eyebrow?: string;
  createLabel: string;
  createAction: string;
  rowActionBasePath: string;
  identityField: string;
  titleField: string;
  searchPlaceholder: string;
  emptyTitle: string;
  emptyDescription: string;
  canCreate?: boolean;
  workspaceHref?: (record: TRecord) => string;
  workspaceLabel?: string;
  columns: CrudColumn<TRecord>[];
  createFields: CrudField[];
  editFields: CrudField[];
  filters?: Array<{
    key: string;
    label: string;
    allLabel: string;
    options: CrudChoice[];
  }>;
  allowedActions: CrudAction[];
};
