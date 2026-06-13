import { useState } from "react";
import { Link, useLocation } from "wouter";
import {
  useGetInitiative,
  useListInitiativeUpdates,
  useCreateInitiativeUpdate,
  getGetInitiativeQueryKey,
  getListInitiativeUpdatesQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Calendar, User, Building2, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";
import { Skeleton } from "@/components/ui/skeleton";

function PriorityPill({ priority }: { priority: string }) {
  const classes: Record<string, string> = {
    high: "bg-red-100 text-red-700 border-red-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`inline-flex items-center border text-xs font-medium rounded px-2 py-0.5 ${classes[priority] ?? classes.low}`}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)} Priority
    </span>
  );
}

export default function InitiativeDetail({ id }: { id: number }) {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [note, setNote] = useState("");
  const [author, setAuthor] = useState("");

  const { data: initiative, isLoading } = useGetInitiative(id, {
    query: { enabled: !!id, queryKey: getGetInitiativeQueryKey(id) },
  });
  const { data: updates, isLoading: updatesLoading } = useListInitiativeUpdates(id, {
    query: { enabled: !!id, queryKey: getListInitiativeUpdatesQueryKey(id) },
  });

  const addUpdate = useCreateInitiativeUpdate({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListInitiativeUpdatesQueryKey(id) });
        setNote("");
        setAuthor("");
      },
    },
  });

  const handleSubmitUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!note.trim() || !author.trim()) return;
    addUpdate.mutate({ id, data: { note: note.trim(), author: author.trim() } });
  };

  if (isLoading) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!initiative) {
    return (
      <div className="p-8 text-center">
        <p className="text-muted-foreground">Initiative not found.</p>
        <Link href="/initiatives"><a className="text-sm text-primary mt-2 inline-block">Back to list</a></Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Back */}
      <Link href="/initiatives" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" />
        All Initiatives
      </Link>

      {/* Header card */}
      <Card className="mb-5">
        <CardContent className="p-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <StatusBadge status={initiative.status} />
                <PriorityPill priority={initiative.priority} />
              </div>
              <h1 className="text-xl font-bold text-foreground">{initiative.title}</h1>
              {initiative.description && (
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{initiative.description}</p>
              )}
            </div>
            <Link href={`/initiatives/${initiative.id}/edit`}>
              <Button variant="outline" size="sm">Edit</Button>
            </Link>
          </div>

          {/* Progress */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Progress</span>
              <span className="text-2xl font-mono font-bold text-foreground">{initiative.progress}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full transition-all bg-primary"
                style={{ width: `${initiative.progress}%` }}
              />
            </div>
          </div>

          {/* Meta fields */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {initiative.owner && (
              <div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mb-0.5"><User className="w-3 h-3" /> Owner</p>
                <p className="text-sm font-medium text-foreground">{initiative.owner}</p>
              </div>
            )}
            {initiative.department && (
              <div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mb-0.5"><Building2 className="w-3 h-3" /> Department</p>
                <p className="text-sm font-medium text-foreground">{initiative.department}</p>
              </div>
            )}
            {initiative.startDate && (
              <div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mb-0.5"><Calendar className="w-3 h-3" /> Start</p>
                <p className="text-sm font-medium text-foreground font-mono">
                  {new Date(initiative.startDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </p>
              </div>
            )}
            {initiative.endDate && (
              <div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mb-0.5"><Calendar className="w-3 h-3" /> Due</p>
                <p className="text-sm font-medium text-foreground font-mono">
                  {new Date(initiative.endDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Updates */}
      <div className="grid md:grid-cols-5 gap-5">
        {/* History */}
        <div className="md:col-span-3">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-3">Progress Log</h2>
          {updatesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
          ) : (updates ?? []).length === 0 ? (
            <Card><CardContent className="p-5 text-sm text-muted-foreground text-center">No updates yet. Add the first one.</CardContent></Card>
          ) : (
            <div className="space-y-2">
              {[...(updates ?? [])].reverse().map((u) => (
                <Card key={u.id}>
                  <CardContent className="p-4">
                    <p className="text-sm text-foreground leading-relaxed">{u.note}</p>
                    <p className="text-xs text-muted-foreground mt-2 font-mono">
                      {u.author} · {new Date(u.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Add update */}
        <div className="md:col-span-2">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-3">Add Update</h2>
          <Card>
            <CardContent className="p-4">
              <form onSubmit={handleSubmitUpdate} className="space-y-3">
                <div>
                  <Label htmlFor="author" className="text-xs">Your name</Label>
                  <Input
                    id="author"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="e.g. Jane Smith"
                    className="h-8 text-sm mt-1"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="note" className="text-xs">Update note</Label>
                  <Textarea
                    id="note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Describe progress, blockers, or key decisions..."
                    rows={4}
                    className="text-sm mt-1 resize-none"
                    required
                  />
                </div>
                <Button
                  type="submit"
                  size="sm"
                  className="w-full gap-1.5"
                  disabled={addUpdate.isPending || !note.trim() || !author.trim()}
                >
                  <Send className="w-3.5 h-3.5" />
                  {addUpdate.isPending ? "Posting..." : "Post Update"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
