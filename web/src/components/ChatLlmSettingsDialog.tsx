import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  FieldGroup,
  FieldLabel,
  Input,
} from "@nqlib/nqui";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { fetchLlmSettings, patchLlmSettings } from "../api";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
};

export function ChatLlmSettingsDialog({ open, onOpenChange, onSaved }: Props) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modelId, setModelId] = useState("");
  const [maxTok, setMaxTok] = useState("");
  const [envHint, setEnvHint] = useState<{ model: string; tokens: number } | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    void fetchLlmSettings()
      .then((s) => {
        setEnvHint({ model: s.environment_model_id, tokens: s.environment_max_new_tokens });
        setModelId(s.stored_model_id ?? "");
        setMaxTok(s.stored_max_new_tokens != null ? String(s.stored_max_new_tokens) : "");
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load settings"))
      .finally(() => setLoading(false));
  }, [open]);

  const save = async () => {
    const modelTrim = modelId.trim();
    const maxTrim = maxTok.trim();
    let maxNum: number | null = null;
    if (maxTrim !== "") {
      maxNum = Number(maxTrim);
      if (!Number.isFinite(maxNum) || maxNum < 32 || maxNum > 8192) {
        toast.error("Max new tokens must be between 32 and 8192");
        return;
      }
    }
    setSaving(true);
    try {
      await patchLlmSettings({
        model_id: modelTrim === "" ? null : modelTrim,
        max_new_tokens: maxTrim === "" ? null : maxNum,
      });
      toast.success("LLM settings saved");
      onSaved();
      onOpenChange(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const resetToEnvironment = async () => {
    setSaving(true);
    try {
      await patchLlmSettings({ model_id: null, max_new_tokens: null });
      toast.success("Cleared overrides — using environment defaults");
      onSaved();
      onOpenChange(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>LLM settings</DialogTitle>
          <DialogDescription>
            Stored in your local SQLite database. Empty fields fall back to{" "}
            <code className="text-xs bg-muted px-1 rounded">LLM_MODEL</code> and{" "}
            <code className="text-xs bg-muted px-1 rounded">LLM_MAX_NEW_TOKENS</code> from the environment.
          </DialogDescription>
        </DialogHeader>
        {envHint && (
          <p className="text-xs text-muted-foreground leading-relaxed">
            Environment defaults: <span className="font-mono break-all">{envHint.model}</span> · max{" "}
            {envHint.tokens} tokens
          </p>
        )}
        <FieldGroup className="gap-3">
          <Field>
            <FieldLabel htmlFor="llm-model-id">Hugging Face model id</FieldLabel>
            <Input
              id="llm-model-id"
              className="font-mono text-xs"
              placeholder={envHint?.model ?? "mlx-community/…"}
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              disabled={loading || saving}
            />
            <p className="text-xs text-muted-foreground mt-1">Leave empty to use the environment default.</p>
          </Field>
          <Field>
            <FieldLabel htmlFor="llm-max-tok">Max new tokens (chat)</FieldLabel>
            <Input
              id="llm-max-tok"
              type="number"
              min={32}
              max={8192}
              placeholder={envHint != null ? String(envHint.tokens) : "512"}
              value={maxTok}
              onChange={(e) => setMaxTok(e.target.value)}
              disabled={loading || saving}
            />
            <p className="text-xs text-muted-foreground mt-1">Leave empty for environment default (32–8192).</p>
          </Field>
        </FieldGroup>
        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
          <Button type="button" variant="outline" size="sm" disabled={saving} onClick={() => void resetToEnvironment()}>
            Clear overrides
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
              Cancel
            </Button>
            <Button type="button" onClick={() => void save()} disabled={loading || saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
