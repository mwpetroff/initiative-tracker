import { useGetDashboardSummary, useGetRecentActivity, useListInitiatives } from "@workspace/api-client-react";
import { Link } from "wouter";
import { TrendingUp, AlertTriangle, Clock, CheckCircle2, Minus, Activity, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function StatCard({
  label,
  value,
  icon: Icon,
  colorClass,
  sub,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  colorClass: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
            <p className={cn("text-3xl font-mono font-bold mt-1", colorClass)}>{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </div>
          <div className={cn("p-2 rounded", colorClass.replace("text-", "bg-").replace("-800", "-100").replace("-500", "-100"))}>
            <Icon className={cn("w-4 h-4", colorClass)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading } = useGetDashboardSummary();
  const { data: activity, isLoading: activityLoading } = useGetRecentActivity({ limit: 8 });
  const { data: initiatives, isLoading: initiativesLoading } = useListInitiatives();

  const atRiskOrDelayed = initiatives?.filter(
    (i) => i.status === "at_risk" || i.status === "delayed"
  ) ?? [];

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Executive Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Organization-wide initiative health</p>
      </div>

      {/* Summary stat cards */}
      {summaryLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}><CardContent className="p-5"><Skeleton className="h-16 w-full" /></CardContent></Card>
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <StatCard label="Total" value={summary.total} icon={Activity} colorClass="text-foreground" />
          <StatCard label="On Track" value={summary.onTrack} icon={TrendingUp} colorClass="text-emerald-600" />
          <StatCard label="At Risk" value={summary.atRisk} icon={AlertTriangle} colorClass="text-amber-600" />
          <StatCard label="Delayed" value={summary.delayed} icon={Clock} colorClass="text-red-600" />
          <StatCard label="Completed" value={summary.completed} icon={CheckCircle2} colorClass="text-blue-600" />
          <StatCard
            label="Avg Progress"
            value={`${Math.round(summary.avgProgress)}%`}
            icon={Minus}
            colorClass="text-foreground"
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Needs attention */}
        <div className="xl:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">Needs Attention</h2>
            <Link href="/initiatives" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {initiativesLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Card key={i}><CardContent className="p-4"><Skeleton className="h-12 w-full" /></CardContent></Card>
              ))}
            </div>
          ) : atRiskOrDelayed.length === 0 ? (
            <Card>
              <CardContent className="p-6 text-center text-sm text-muted-foreground">
                No initiatives currently at risk or delayed.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {atRiskOrDelayed.map((initiative) => (
                <Link key={initiative.id} href={`/initiatives/${initiative.id}`} className="block">
                  <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <StatusBadge status={initiative.status} />
                            {initiative.priority === "high" && (
                              <span className="text-xs text-muted-foreground border border-dashed border-border px-1.5 py-0.5 rounded">High Priority</span>
                            )}
                          </div>
                          <p className="text-sm font-medium text-foreground truncate">{initiative.title}</p>
                          {initiative.owner && (
                            <p className="text-xs text-muted-foreground mt-0.5">{initiative.owner} · {initiative.department}</p>
                          )}
                        </div>
                        <div className="w-24 shrink-0">
                          <ProgressBar progress={initiative.progress} status={initiative.status} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}

          {/* By Department */}
          {summary && summary.byDepartment.length > 0 && (
            <div className="mt-6">
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-3">By Department</h2>
              <Card>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Department</th>
                        <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Initiatives</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.byDepartment.sort((a, b) => b.count - a.count).map((row) => (
                        <tr key={row.department} className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2.5 text-foreground">{row.department}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-muted-foreground">{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div>
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-3">Recent Activity</h2>
          {activityLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {(activity ?? []).map((item) => (
                <Link key={item.id} href={`/initiatives/${item.initiativeId}`} className="block">
                  <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="p-3.5">
                      <p className="text-xs font-medium text-foreground mb-1 leading-snug">{item.initiativeTitle}</p>
                      <p className="text-xs text-muted-foreground leading-snug line-clamp-2">{item.note}</p>
                      <p className="text-xs text-muted-foreground mt-1.5 font-mono">{item.author} · {new Date(item.createdAt).toLocaleDateString()}</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
              {(!activity || activity.length === 0) && (
                <Card><CardContent className="p-4 text-center text-xs text-muted-foreground">No recent activity</CardContent></Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
