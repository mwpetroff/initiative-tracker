import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import {
  useGetInitiative,
  useCreateInitiative,
  useUpdateInitiative,
  useListDepartments,
  getListInitiativesQueryKey,
  getGetInitiativeQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";

const STATUSES = [
  { value: "not_started", label: "Not Started" },
  { value: "on_track", label: "On Track" },
  { value: "at_risk", label: "At Risk" },
  { value: "delayed", label: "Delayed" },
  { value: "completed", label: "Completed" },
];

const PRIORITIES = [
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

interface FormFields {
  title: string;
  description: string;
  status: string;
  progress: number;
  priority: string;
  owner: string;
  department: string;
  startDate: string;
  endDate: string;
}

const DEFAULT: FormFields = {
  title: "",
  description: "",
  status: "not_started",
  progress: 0,
  priority: "medium",
  owner: "",
  department: "",
  startDate: "",
  endDate: "",
};

export default function InitiativeForm({ id }: { id?: number }) {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const isEdit = !!id;

  const [fields, setFields] = useState<FormFields>(DEFAULT);

  const { data: existing } = useGetInitiative(id ?? 0, {
    query: { enabled: isEdit, queryKey: getGetInitiativeQueryKey(id ?? 0) },
  });

  const { data: departments } = useListDepartments();

  const createMutation = useCreateInitiative({
    mutation: {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: getListInitiativesQueryKey() });
        navigate(`/initiatives/${data.id}`);
      },
    },
  });

  const updateMutation = useUpdateInitiative({
    mutation: {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: getListInitiativesQueryKey() });
        queryClient.invalidateQueries({ queryKey: getGetInitiativeQueryKey(data.id) });
        navigate(`/initiatives/${data.id}`);
      },
    },
  });

  useEffect(() => {
    if (existing) {
      setFields({
        title: existing.title ?? "",
        description: existing.description ?? "",
        status: existing.status ?? "not_started",
        progress: existing.progress ?? 0,
        priority: existing.priority ?? "medium",
        owner: existing.owner ?? "",
        department: existing.department ?? "",
        startDate: existing.startDate ?? "",
        endDate: existing.endDate ?? "",
      });
    }
  }, [existing]);

  const set = (key: keyof FormFields, value: string | number) =>
    setFields((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      title: fields.title,
      description: fields.description || undefined,
      status: fields.status as any,
      progress: fields.progress,
      priority: fields.priority as any,
      owner: fields.owner || undefined,
      department: fields.department || undefined,
      startDate: fields.startDate || undefined,
      endDate: fields.endDate || undefined,
    };
    if (isEdit && id) {
      updateMutation.mutate({ id, data: payload });
    } else {
      createMutation.mutate({ data: payload });
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <a
        href="#"
        onClick={(e) => { e.preventDefault(); navigate(isEdit && id ? `/initiatives/${id}` : "/initiatives"); }}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        {isEdit ? "Back to initiative" : "Back to list"}
      </a>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">{isEdit ? "Edit Initiative" : "New Initiative"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="title" className="text-xs">Title <span className="text-destructive">*</span></Label>
              <Input
                id="title"
                value={fields.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder="e.g. ERP System Migration"
                className="mt-1"
                required
              />
            </div>

            <div>
              <Label htmlFor="description" className="text-xs">Description</Label>
              <Textarea
                id="description"
                value={fields.description}
                onChange={(e) => set("description", e.target.value)}
                placeholder="What is this initiative trying to achieve?"
                rows={3}
                className="mt-1 resize-none text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs">Status <span className="text-destructive">*</span></Label>
                <Select value={fields.status} onValueChange={(v) => set("status", v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUSES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Priority <span className="text-destructive">*</span></Label>
                <Select value={fields.priority} onValueChange={(v) => set("priority", v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs">Progress — <span className="font-mono">{fields.progress}%</span></Label>
              <div className="mt-3 px-1">
                <Slider
                  min={0}
                  max={100}
                  step={5}
                  value={[fields.progress]}
                  onValueChange={([v]) => set("progress", v)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="owner" className="text-xs">Owner</Label>
                <Input
                  id="owner"
                  value={fields.owner}
                  onChange={(e) => set("owner", e.target.value)}
                  placeholder="e.g. Jane Smith"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Department</Label>
                <Select value={fields.department || "__none"} onValueChange={(v) => set("department", v === "__none" ? "" : v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">None</SelectItem>
                    {(departments ?? []).map((d) => (
                      <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="startDate" className="text-xs">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={fields.startDate}
                  onChange={(e) => set("startDate", e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="endDate" className="text-xs">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={fields.endDate}
                  onChange={(e) => set("endDate", e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => navigate(isEdit && id ? `/initiatives/${id}` : "/initiatives")}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isPending || !fields.title} className="gap-1.5">
                <Save className="w-3.5 h-3.5" />
                {isPending ? "Saving..." : isEdit ? "Save Changes" : "Create Initiative"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
