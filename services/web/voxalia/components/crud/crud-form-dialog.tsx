"use client";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { PasswordInput } from "@/components/ui/password-input";
import { CrudField } from "./types";

function valuesFor(field: CrudField, record?: Record<string, unknown>) {
  if (!record) return [];
  const valueKey = field.sourceName ?? field.name;
  const value = record[valueKey];
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && field.control === "checkbox-group") {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }
  return value === null || value === undefined ? [] : [String(value)];
}

function Field({
  field,
  mode,
  record
}: {
  field: CrudField;
  mode: "create" | "view" | "edit";
  record?: Record<string, unknown>;
}) {
  if ((field.createOnly && mode !== "create") || (field.editOnly && mode === "view")) return null;

  const value = valuesFor(field, record)[0] ?? field.defaultValue ?? "";
  const values = valuesFor(field, record);
  const readOnly = mode === "view" || field.editable === false;
  const options = field.optionsSource && record && Array.isArray(record[field.optionsSource])
    ? (record[field.optionsSource] as Array<{ value: string; label: string }>)
    : field.options;

  return (
    <label className="space-y-1 text-label font-medium">
      <span>{field.label}</span>
      {field.control === "checkbox-group" && options ? (
        <div className="grid gap-2 rounded-md border border-border-2 bg-background p-3">
          {options.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-body-sm font-normal">
              <input
                type="checkbox"
                name={field.name}
                value={option.value}
                defaultChecked={values.includes(option.value)}
                disabled={readOnly}
                className="h-4 w-4 rounded border-border-2"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      ) : options && !readOnly ? (
        <select
          name={field.name}
          defaultValue={value}
          required={field.required ?? true}
          className="min-h-9 w-full rounded-md border border-border-2 bg-background px-3 py-2 text-body-sm outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : field.type === "password" && !readOnly ? (
        <PasswordInput
          name={field.name}
          required={field.required ?? true}
          minLength={field.minLength}
          defaultValue={value}
          autoComplete="new-password"
          placeholder={field.placeholder}
          className="h-9 w-full rounded-md border border-border-2 bg-background px-3 text-body-sm outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
        />
      ) : (
        <input
          name={field.name}
          type={field.type ?? "text"}
          required={readOnly ? false : field.required ?? true}
          minLength={field.minLength}
          defaultValue={value}
          readOnly={readOnly}
          placeholder={field.placeholder}
          className="h-9 w-full rounded-md border border-border-2 bg-background px-3 text-body-sm outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background read-only:bg-surface-2"
        />
      )}
      {field.helperText ? <span className="block text-meta font-normal text-muted-foreground">{field.helperText}</span> : null}
    </label>
  );
}

export function CrudFormDialog({
  open,
  mode,
  title,
  description,
  action,
  fields,
  record,
  canSubmit = true,
  onClose
}: {
  open: boolean;
  mode: "create" | "view" | "edit";
  title: string;
  description?: string;
  action?: string;
  fields: CrudField[];
  record?: Record<string, unknown>;
  canSubmit?: boolean;
  onClose: () => void;
}) {
  return (
    <Modal open={open} title={title} description={description} onClose={onClose}>
      <form action={mode !== "view" && canSubmit ? action : undefined} method="post" className="space-y-5">
        <div className="grid gap-3 md:grid-cols-2">
          {fields.map((field) => (
            <Field key={field.name} field={field} mode={mode} record={record} />
          ))}
        </div>
        <div className="flex justify-end gap-2 border-t pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            {mode === "view" ? "Close" : "Cancel"}
          </Button>
          {mode !== "view" ? (
            <Button type="submit" disabled={!canSubmit}>
              {mode === "create" ? "Create" : "Update"}
            </Button>
          ) : null}
        </div>
      </form>
    </Modal>
  );
}
